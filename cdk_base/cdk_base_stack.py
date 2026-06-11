from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_events as events,
    aws_events_targets as targets,
    aws_logs as logs,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_iam as iam,
    aws_dynamodb as dynamodb,
    aws_sns as sns,
    aws_kms as kms,
    aws_lambda as lambda_,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    RemovalPolicy,
    Duration,
)
from constructs import Construct

class CdkBaseStack(Stack):

    def __init__(
        self, 
        scope: Construct, 
        construct_id: str, 
        env_name: str = "dev",
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.template_options.description = "Event-driven sleep audio pipeline base infrastructure"
        
        # Store environment name for configuration
        self.env_name = env_name
        
        # Environment-specific configuration
        # Dev: aggressive cleanup policies, shorter retention
        # Stage: similar to dev for easy testing
        # Prod: data retention, longer logs, more conservative policies
        is_production = (env_name == "prod")
        is_dev = (env_name == "dev")
        
        # Removal policy: RETAIN for prod, DESTROY for dev/stage
        removal_policy = RemovalPolicy.RETAIN if is_production else RemovalPolicy.DESTROY
        
        # Log retention: 90 days for prod, 7 days for dev (using enum values)
        log_retention = logs.RetentionDays.THREE_MONTHS if is_production else logs.RetentionDays.ONE_WEEK
        
        # Auto-delete S3 objects: only in dev/stage, not prod
        auto_delete_objects = not is_production

        # Input S3 Bucket - receives raw audio uploads
        self.input_bucket = s3.Bucket(
            self,
            "SleepAudioInputBucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=removal_policy,
            auto_delete_objects=auto_delete_objects,
            event_bridge_enabled=True,  # Enable EventBridge notifications
        )

        # Output S3 Bucket - stores processed audio files
        self.output_bucket = s3.Bucket(
            self,
            "SleepAudioOutputBucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=removal_policy,
            auto_delete_objects=auto_delete_objects,
        )

        # DynamoDB Table - stores audio pipeline metadata
        self.metadata_table = dynamodb.Table(
            self,
            "SleepAudioMetadataTable",
            partition_key=dynamodb.Attribute(
                name="audioId",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            encryption=dynamodb.TableEncryption.AWS_MANAGED,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True
            ),
            removal_policy=removal_policy,
        )

        # SNS Topics for notifications
        # KMS Key for SNS topic encryption
        sns_encryption_key = kms.Key(
            self,
            "SnsEncryptionKey",
            description="KMS key for SNS topic encryption",
            enable_key_rotation=True,
            removal_policy=removal_policy,
        )

        # SNS Topic for pipeline completion notifications
        self.completed_topic = sns.Topic(
            self,
            "SleepAudioPipelineCompleted",
            display_name="Sleep Audio Pipeline Completed",
            master_key=sns_encryption_key,
        )

        # SNS Topic for pipeline failure notifications
        self.failed_topic = sns.Topic(
            self,
            "SleepAudioPipelineFailed",
            display_name="Sleep Audio Pipeline Failed",
            master_key=sns_encryption_key,
        )

        # Lambda Function - Audio Processor (full audio processing implementation)
        self.audio_processor_function = lambda_.Function(
            self,
            "SleepAudioProcessor",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="audio_processor.handler",
            code=lambda_.Code.from_asset("lambda"),
            environment={
                "METADATA_TABLE_NAME": self.metadata_table.table_name,
                "OUTPUT_BUCKET_NAME": self.output_bucket.bucket_name
            },
            description="Processes audio files - downloads input, generates sleep audio with Polly, uploads to output bucket",
            tracing=lambda_.Tracing.ACTIVE,  # Enable X-Ray tracing
            timeout=Duration.seconds(60),  # Increase timeout for audio processing
        )

        # Grant Lambda permissions
        # 1. Read from DynamoDB table (for future metadata operations)
        self.metadata_table.grant_read_data(self.audio_processor_function)
        
        # 2. Read from Input S3 bucket
        self.input_bucket.grant_read(self.audio_processor_function)
        
        # 3. Write to Output S3 bucket
        self.output_bucket.grant_write(self.audio_processor_function)
        
        # 4. Polly synthesize permission
        self.audio_processor_function.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["polly:SynthesizeSpeech"],
                resources=["*"]  # Polly SynthesizeSpeech doesn't support resource-level permissions
            )
        )

        # CloudWatch Log Group for Step Functions state machine logging
        state_machine_log_group = logs.LogGroup(
            self,
            "StateMachineLogGroup",
            removal_policy=removal_policy,
            retention=log_retention,
        )

        # Step Functions State Machine - Sleep Audio Pipeline
        # Task 1: Write initial metadata to DynamoDB
        write_metadata_task = tasks.DynamoPutItem(
            self,
            "WriteInitialMetadata",
            table=self.metadata_table,
            item={
                "audioId": tasks.DynamoAttributeValue.from_string(
                    sfn.JsonPath.string_at("$.detail.object.key")
                ),
                "status": tasks.DynamoAttributeValue.from_string("PROCESSING"),
                "inputBucket": tasks.DynamoAttributeValue.from_string(
                    sfn.JsonPath.string_at("$.detail.bucket.name")
                ),
                "inputKey": tasks.DynamoAttributeValue.from_string(
                    sfn.JsonPath.string_at("$.detail.object.key")
                ),
                "createdAt": tasks.DynamoAttributeValue.from_string(
                    sfn.JsonPath.string_at("$$.Execution.StartTime")
                ),
                "updatedAt": tasks.DynamoAttributeValue.from_string(
                    sfn.JsonPath.string_at("$$.Execution.StartTime")
                ),
            },
            result_path="$.metadata"
        )
        
        # Add retry policy for DynamoDB write task
        write_metadata_task.add_retry(
            errors=["DynamoDB.ProvisionedThroughputExceededException", "States.TaskFailed"],
            interval=Duration.seconds(1),
            max_attempts=3,
            backoff_rate=2.0
        )

        # Task 2: Invoke Lambda for audio processing/validation
        invoke_audio_processor = tasks.LambdaInvoke(
            self,
            "InvokeAudioProcessor",
            lambda_function=self.audio_processor_function,
            # Pass the entire event payload to the Lambda
            payload=sfn.TaskInput.from_object({
                "detail": sfn.JsonPath.object_at("$.detail"),
                "metadata": sfn.JsonPath.object_at("$.metadata")
            }),
            result_path="$.processorResult",
            # Extract the Payload from Lambda's response
            output_path="$",
            # Add retry policy with exponential backoff
            retry_on_service_exceptions=True,
        )
        
        # Add additional retry configuration for Lambda-specific errors
        invoke_audio_processor.add_retry(
            errors=["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"],
            interval=Duration.seconds(2),
            max_attempts=3,
            backoff_rate=2.0
        )

        # Task 3: Invoke Polly for text-to-speech (skeleton from Issue #4)
        # Note: This is a skeleton implementation. The actual text input will be provided
        # after validation and processing steps are added in future issues.
        polly_task = tasks.CallAwsService(
            self,
            "InvokePolly",
            service="polly",
            action="synthesizeSpeech",
            parameters={
                "Text": "Placeholder text for skeleton implementation",
                "VoiceId": "Joanna",
                "OutputFormat": "mp3",
                "Engine": "neural"
            },
            iam_resources=[
                # SynthesizeSpeech doesn't operate on specific resources
                # Scoped to account-level Polly access only
                f"arn:aws:polly:{self.region}:{self.account}:lexicon/*"
            ],
            result_path="$.pollyResult"
        )
        
        # Add retry policy for Polly task
        polly_task.add_retry(
            errors=["Polly.ServiceFailureException", "States.TaskFailed"],
            interval=Duration.seconds(2),
            max_attempts=3,
            backoff_rate=2.0
        )

        # Task 4: Update DynamoDB status to COMPLETED on success
        update_completed_status = tasks.DynamoUpdateItem(
            self,
            "UpdateStatusCompleted",
            table=self.metadata_table,
            key={
                "audioId": tasks.DynamoAttributeValue.from_string(
                    sfn.JsonPath.string_at("$.detail.object.key")
                )
            },
            update_expression="SET #status = :completed, #updatedAt = :timestamp, #outputBucket = :outputBucket, #outputKey = :outputKey, #outputSize = :outputSize",
            expression_attribute_names={
                "#status": "status",
                "#updatedAt": "updatedAt",
                "#outputBucket": "outputBucket",
                "#outputKey": "outputKey",
                "#outputSize": "outputSize"
            },
            expression_attribute_values={
                ":completed": tasks.DynamoAttributeValue.from_string("COMPLETED"),
                ":timestamp": tasks.DynamoAttributeValue.from_string(
                    sfn.JsonPath.string_at("$$.State.EnteredTime")
                ),
                ":outputBucket": tasks.DynamoAttributeValue.from_string(
                    sfn.JsonPath.string_at("$.processorResult.Payload.outputBucket")
                ),
                ":outputKey": tasks.DynamoAttributeValue.from_string(
                    sfn.JsonPath.string_at("$.processorResult.Payload.outputKey")
                ),
                ":outputSize": tasks.DynamoAttributeValue.from_number(
                    sfn.JsonPath.number_at("$.processorResult.Payload.outputSize")
                )
            },
            result_path="$.statusUpdate"
        )
        
        # Add retry policy for DynamoDB update task
        update_completed_status.add_retry(
            errors=["DynamoDB.ProvisionedThroughputExceededException", "States.TaskFailed"],
            interval=Duration.seconds(1),
            max_attempts=3,
            backoff_rate=2.0
        )

        # Task 5: Publish success notification to SNS
        publish_success_notification = tasks.SnsPublish(
            self,
            "PublishSuccessNotification",
            topic=self.completed_topic,
            message=sfn.TaskInput.from_object({
                "status": "COMPLETED",
                "audioId": sfn.JsonPath.string_at("$.detail.object.key"),
                "executionId": sfn.JsonPath.string_at("$$.Execution.Name"),
                "timestamp": sfn.JsonPath.string_at("$$.State.EnteredTime")
            }),
            subject="Sleep Audio Pipeline - Processing Completed",
            result_path="$.notification"
        )

        # Task 6: Update DynamoDB status to FAILED on error
        update_failed_status = tasks.DynamoUpdateItem(
            self,
            "UpdateStatusFailed",
            table=self.metadata_table,
            key={
                "audioId": tasks.DynamoAttributeValue.from_string(
                    sfn.JsonPath.string_at("$.detail.object.key")
                )
            },
            update_expression="SET #status = :failed, #updatedAt = :timestamp, #error = :errorInfo",
            expression_attribute_names={
                "#status": "status",
                "#updatedAt": "updatedAt",
                "#error": "errorInfo"
            },
            expression_attribute_values={
                ":failed": tasks.DynamoAttributeValue.from_string("FAILED"),
                ":timestamp": tasks.DynamoAttributeValue.from_string(
                    sfn.JsonPath.string_at("$$.State.EnteredTime")
                ),
                ":errorInfo": tasks.DynamoAttributeValue.from_string(
                    sfn.JsonPath.string_at("States.Format('Error: {}', $.error)")
                )
            },
            result_path="$.statusUpdate"
        )
        
        # Add retry policy for DynamoDB failure update task
        update_failed_status.add_retry(
            errors=["DynamoDB.ProvisionedThroughputExceededException", "States.TaskFailed"],
            interval=Duration.seconds(1),
            max_attempts=3,
            backoff_rate=2.0
        )

        # Task 7: Publish failure notification to SNS
        publish_failure_notification = tasks.SnsPublish(
            self,
            "PublishFailureNotification",
            topic=self.failed_topic,
            message=sfn.TaskInput.from_object({
                "status": "FAILED",
                "audioId": sfn.JsonPath.string_at("$.detail.object.key"),
                "executionId": sfn.JsonPath.string_at("$$.Execution.Name"),
                "timestamp": sfn.JsonPath.string_at("$$.State.EnteredTime"),
                "error": sfn.JsonPath.string_at("$.error")
            }),
            subject="Sleep Audio Pipeline - Processing Failed",
            result_path="$.notification"
        )

        # Success path: Lambda -> Polly -> Update Status -> Notify Success
        success_chain = invoke_audio_processor.next(polly_task).next(update_completed_status).next(publish_success_notification)

        # Failure path: Update Status -> Notify Failure
        failure_chain = update_failed_status.next(publish_failure_notification)

        # Add error handling to the main workflow
        # Catch errors from any task and route to failure path
        write_metadata_task.add_catch(
            failure_chain,
            errors=["States.ALL"],
            result_path="$.error"
        )

        invoke_audio_processor.add_catch(
            failure_chain,
            errors=["States.ALL"],
            result_path="$.error"
        )

        polly_task.add_catch(
            failure_chain,
            errors=["States.ALL"],
            result_path="$.error"
        )

        update_completed_status.add_catch(
            failure_chain,
            errors=["States.ALL"],
            result_path="$.error"
        )

        publish_success_notification.add_catch(
            failure_chain,
            errors=["States.ALL"],
            result_path="$.error"
        )

        # Chain the tasks together: DynamoDB write -> Lambda -> Polly -> Success Path
        definition = write_metadata_task.next(success_chain)

        # Define the state machine
        self.state_machine = sfn.StateMachine(
            self,
            "SleepAudioPipelineStateMachine",
            definition_body=sfn.DefinitionBody.from_chainable(definition),
            logs=sfn.LogOptions(
                destination=state_machine_log_group,
                level=sfn.LogLevel.ALL,
                include_execution_data=True
            ),
            tracing_enabled=True,
        )

        # EventBridge Rule - triggers on S3 Object Created events from Input Bucket
        self.processing_rule = events.Rule(
            self,
            "SleepAudioProcessingRule",
            description="Triggers processing workflow when audio is uploaded to input bucket",
            event_pattern=events.EventPattern(
                source=["aws.s3"],
                detail_type=["Object Created"],
                detail={
                    "bucket": {
                        "name": [self.input_bucket.bucket_name]
                    }
                }
            ),
            enabled=True,
        )

        # Add Step Functions state machine as target
        self.processing_rule.add_target(
            targets.SfnStateMachine(
                self.state_machine,
                input=events.RuleTargetInput.from_event_path("$")
            )
        )

        # CloudWatch Alarms for Observability (Issue #10)
        # Alarm 1: State Machine Execution Failures
        self.state_machine_failure_alarm = cloudwatch.Alarm(
            self,
            "StateMachineExecutionFailuresAlarm",
            metric=self.state_machine.metric_failed(
                statistic="Sum",
                period=Duration.minutes(5)
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            alarm_description="Alert when Step Functions state machine executions fail",
            alarm_name=f"SleepAudioPipeline-{env_name}-StateMachineFailures",
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        
        # Add SNS action to notify on alarm
        self.state_machine_failure_alarm.add_alarm_action(
            cw_actions.SnsAction(self.failed_topic)
        )
        
        # Alarm 2: Lambda Function Errors
        self.lambda_errors_alarm = cloudwatch.Alarm(
            self,
            "LambdaErrorsAlarm",
            metric=self.audio_processor_function.metric_errors(
                statistic="Sum",
                period=Duration.minutes(5)
            ),
            threshold=5,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            alarm_description="Alert when Lambda function errors exceed threshold",
            alarm_name=f"SleepAudioPipeline-{env_name}-LambdaErrors",
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        
        # Add SNS action to notify on alarm
        self.lambda_errors_alarm.add_alarm_action(
            cw_actions.SnsAction(self.failed_topic)
        )
