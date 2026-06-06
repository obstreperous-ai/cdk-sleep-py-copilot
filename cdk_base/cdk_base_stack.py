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
    RemovalPolicy,
)
from constructs import Construct

class CdkBaseStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.template_options.description = "Event-driven sleep audio pipeline base infrastructure"

        # Input S3 Bucket - receives raw audio uploads
        self.input_bucket = s3.Bucket(
            self,
            "SleepAudioInputBucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,  # For dev/test - should be RETAIN in prod
            auto_delete_objects=True,  # For dev/test - should be False in prod
            event_bridge_enabled=True,  # Enable EventBridge notifications
        )

        # Output S3 Bucket - stores processed audio files
        self.output_bucket = s3.Bucket(
            self,
            "SleepAudioOutputBucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,  # For dev/test - should be RETAIN in prod
            auto_delete_objects=True,  # For dev/test - should be False in prod
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
            removal_policy=RemovalPolicy.DESTROY,  # For dev/test - should be RETAIN in prod
        )

        # SNS Topics for notifications
        # KMS Key for SNS topic encryption
        sns_encryption_key = kms.Key(
            self,
            "SnsEncryptionKey",
            description="KMS key for SNS topic encryption",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.DESTROY,  # For dev/test - should be RETAIN in prod
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

        # CloudWatch Log Group for Step Functions state machine logging
        state_machine_log_group = logs.LogGroup(
            self,
            "StateMachineLogGroup",
            removal_policy=RemovalPolicy.DESTROY,
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

        # Task 2: Invoke Polly for text-to-speech (skeleton from Issue #4)
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

        # Task 3: Update DynamoDB status to COMPLETED on success
        update_completed_status = tasks.DynamoUpdateItem(
            self,
            "UpdateStatusCompleted",
            table=self.metadata_table,
            key={
                "audioId": tasks.DynamoAttributeValue.from_string(
                    sfn.JsonPath.string_at("$.detail.object.key")
                )
            },
            update_expression="SET #status = :completed, #updatedAt = :timestamp",
            expression_attribute_names={
                "#status": "status",
                "#updatedAt": "updatedAt"
            },
            expression_attribute_values={
                ":completed": tasks.DynamoAttributeValue.from_string("COMPLETED"),
                ":timestamp": tasks.DynamoAttributeValue.from_string(
                    sfn.JsonPath.string_at("$$.State.EnteredTime")
                )
            },
            result_path="$.statusUpdate"
        )

        # Task 4: Publish success notification to SNS
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

        # Task 5: Update DynamoDB status to FAILED on error
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

        # Task 6: Publish failure notification to SNS
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

        # Success path: Polly -> Update Status -> Notify Success
        success_chain = polly_task.next(update_completed_status).next(publish_success_notification)

        # Failure path: Update Status -> Notify Failure
        failure_chain = update_failed_status.next(publish_failure_notification)

        # Add error handling to the main workflow
        # Catch errors from any task and route to failure path
        write_metadata_task.add_catch(
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

        # Chain the tasks together: DynamoDB write -> Polly -> Success Path
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
