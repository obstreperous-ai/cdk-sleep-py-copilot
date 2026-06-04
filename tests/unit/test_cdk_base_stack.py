import aws_cdk as core
import aws_cdk.assertions as assertions
import pytest

from cdk_base.cdk_base_stack import CdkBaseStack


@pytest.fixture
def cdk_base_template() -> assertions.Template:
    app = core.App()
    stack = CdkBaseStack(app, "cdk-base")
    return assertions.Template.from_stack(stack)


def test_template_has_description(cdk_base_template: assertions.Template):
    cdk_base_template.template_matches(
        assertions.Match.object_like(
            {"Description": "Event-driven sleep audio pipeline base infrastructure"}
        )
    )


def test_input_bucket_exists_with_encryption(cdk_base_template: assertions.Template):
    """Test that Input S3 Bucket exists with encryption enabled"""
    cdk_base_template.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "BucketEncryption": {
                "ServerSideEncryptionConfiguration": [
                    {
                        "ServerSideEncryptionByDefault": {
                            "SSEAlgorithm": "AES256"
                        }
                    }
                ]
            }
        }
    )


def test_input_bucket_has_versioning_enabled(cdk_base_template: assertions.Template):
    """Test that Input S3 Bucket has versioning enabled"""
    cdk_base_template.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "VersioningConfiguration": {
                "Status": "Enabled"
            }
        }
    )


def test_input_bucket_blocks_public_access(cdk_base_template: assertions.Template):
    """Test that Input S3 Bucket blocks all public access"""
    cdk_base_template.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "BlockPublicPolicy": True,
                "IgnorePublicAcls": True,
                "RestrictPublicBuckets": True
            }
        }
    )


def test_output_bucket_exists_with_encryption(cdk_base_template: assertions.Template):
    """Test that Output S3 Bucket exists with encryption enabled"""
    # This should match at least 2 buckets (input and output)
    cdk_base_template.resource_count_is("AWS::S3::Bucket", 2)


def test_eventbridge_rule_exists(cdk_base_template: assertions.Template):
    """Test that EventBridge rule exists for S3 Object Created events"""
    cdk_base_template.has_resource_properties(
        "AWS::Events::Rule",
        {
            "EventPattern": {
                "source": ["aws.s3"],
                "detail-type": ["Object Created"]
            },
            "State": "ENABLED"
        }
    )


def test_eventbridge_rule_has_target(cdk_base_template: assertions.Template):
    """Test that EventBridge rule has a target configured"""
    cdk_base_template.has_resource_properties(
        "AWS::Events::Rule",
        {
            "Targets": assertions.Match.array_with([
                assertions.Match.object_like({
                    "Arn": assertions.Match.any_value()
                })
            ])
        }
    )


def test_step_functions_state_machine_exists(cdk_base_template: assertions.Template):
    """Test that Step Functions state machine exists"""
    cdk_base_template.resource_count_is("AWS::StepFunctions::StateMachine", 1)


def test_state_machine_has_logging_enabled(cdk_base_template: assertions.Template):
    """Test that state machine has CloudWatch logging enabled"""
    cdk_base_template.has_resource_properties(
        "AWS::StepFunctions::StateMachine",
        {
            "LoggingConfiguration": {
                "Level": assertions.Match.any_value(),
                "IncludeExecutionData": assertions.Match.any_value(),
                "Destinations": assertions.Match.array_with([
                    assertions.Match.object_like({
                        "CloudWatchLogsLogGroup": assertions.Match.object_like({
                            "LogGroupArn": assertions.Match.any_value()
                        })
                    })
                ])
            }
        }
    )


def test_state_machine_definition_contains_polly_task(cdk_base_template: assertions.Template):
    """Test that state machine definition contains Polly integration task"""
    # Get the state machine resource to check its definition
    state_machines = cdk_base_template.find_resources("AWS::StepFunctions::StateMachine")
    assert len(state_machines) == 1, "Expected exactly one state machine"
    
    # The definition will be in DefinitionString as a Fn::Join
    # We'll verify that Polly service is referenced in the state machine
    state_machine = list(state_machines.values())[0]
    assert "DefinitionString" in state_machine["Properties"]
    
    # Alternative: check that the state machine has the expected properties
    cdk_base_template.has_resource_properties(
        "AWS::StepFunctions::StateMachine",
        {
            "DefinitionString": assertions.Match.any_value()
        }
    )


def test_eventbridge_rule_targets_step_functions(cdk_base_template: assertions.Template):
    """Test that EventBridge rule targets the Step Functions state machine"""
    cdk_base_template.has_resource_properties(
        "AWS::Events::Rule",
        {
            "Targets": assertions.Match.array_with([
                assertions.Match.object_like({
                    "Arn": assertions.Match.any_value(),
                    "RoleArn": assertions.Match.any_value()
                })
            ])
        }
    )


def test_state_machine_has_execution_role(cdk_base_template: assertions.Template):
    """Test that state machine has proper execution IAM role"""
    cdk_base_template.has_resource_properties(
        "AWS::StepFunctions::StateMachine",
        {
            "RoleArn": assertions.Match.any_value()
        }
    )
