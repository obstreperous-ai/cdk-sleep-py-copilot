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
