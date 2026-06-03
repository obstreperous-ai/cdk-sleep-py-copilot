from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_events as events,
    aws_events_targets as targets,
    aws_logs as logs,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_iam as iam,
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

        # CloudWatch Log Group for Step Functions state machine logging
        state_machine_log_group = logs.LogGroup(
            self,
            "StateMachineLogGroup",
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Step Functions State Machine - Sleep Audio Pipeline
        # Define the Polly task using CallAwsService for minimal integration
        polly_task = tasks.CallAwsService(
            self,
            "InvokePolly",
            service="polly",
            action="synthesizeSpeech",
            parameters={
                "Text": sfn.JsonPath.string_at("$.text"),
                "VoiceId": "Joanna",
                "OutputFormat": "mp3",
                "Engine": "neural"
            },
            iam_resources=["*"],  # Will be scoped down in production
            result_path="$.pollyResult"
        )

        # Define the state machine
        self.state_machine = sfn.StateMachine(
            self,
            "SleepAudioPipelineStateMachine",
            definition_body=sfn.DefinitionBody.from_chainable(polly_task),
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
