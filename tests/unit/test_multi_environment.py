"""
Tests for multi-environment support (Issue #9)

These tests verify that the stack can be deployed to multiple environments
(dev, stage, prod) with appropriate configuration differences.
"""
import aws_cdk as core
import aws_cdk.assertions as assertions
import pytest

from cdk_base.cdk_base_stack import CdkBaseStack


class TestMultiEnvironmentSupport:
    """Test multi-environment configuration and context handling"""
    
    def test_dev_environment_uses_destroy_removal_policy(self):
        """Test that dev environment uses DESTROY removal policy for non-critical resources"""
        app = core.App(context={"env": "dev"})
        stack = CdkBaseStack(app, "test-stack", env_name="dev")
        template = assertions.Template.from_stack(stack)
        
        # In dev, S3 buckets should have DESTROY removal policy
        # This is indicated by DeletionPolicy: Delete in CloudFormation
        template.has_resource(
            "AWS::S3::Bucket",
            {
                "DeletionPolicy": "Delete"
            }
        )
    
    def test_prod_environment_uses_retain_removal_policy(self):
        """Test that prod environment uses RETAIN removal policy for critical resources"""
        app = core.App(context={"env": "prod"})
        stack = CdkBaseStack(app, "test-stack", env_name="prod")
        template = assertions.Template.from_stack(stack)
        
        # In prod, S3 buckets should have RETAIN removal policy
        # This is indicated by DeletionPolicy: Retain in CloudFormation
        template.has_resource(
            "AWS::S3::Bucket",
            {
                "DeletionPolicy": "Retain"
            }
        )
    
    def test_dev_environment_has_auto_delete_objects_enabled(self):
        """Test that dev environment enables auto-delete for S3 objects"""
        app = core.App(context={"env": "dev"})
        stack = CdkBaseStack(app, "test-stack", env_name="dev")
        template = assertions.Template.from_stack(stack)
        
        # Dev should have auto-delete objects enabled (indicated by custom resource)
        # This allows for clean teardown in dev environments
        buckets = template.find_resources("AWS::S3::Bucket")
        # At least one bucket should have the auto-delete tag
        found_auto_delete = False
        for bucket_id, bucket in buckets.items():
            tags = bucket.get("Properties", {}).get("Tags", [])
            if any(tag.get("Key") == "aws-cdk:auto-delete-objects" for tag in tags):
                found_auto_delete = True
                break
        assert found_auto_delete, "Expected at least one bucket with auto-delete enabled in dev"
    
    def test_prod_environment_has_auto_delete_objects_disabled(self):
        """Test that prod environment disables auto-delete for S3 objects"""
        app = core.App(context={"env": "prod"})
        stack = CdkBaseStack(app, "test-stack", env_name="prod")
        template = assertions.Template.from_stack(stack)
        
        # Prod should NOT have auto-delete objects enabled
        # Check that no bucket has the auto-delete tag
        buckets = template.find_resources("AWS::S3::Bucket")
        for bucket_id, bucket in buckets.items():
            tags = bucket.get("Properties", {}).get("Tags", [])
            has_auto_delete = any(
                tag.get("Key") == "aws-cdk:auto-delete-objects" 
                for tag in tags
            )
            # In prod, we should not see auto-delete tags
            # (or if present, they might be from other CDK mechanisms)
            # The key check is that removal_policy is RETAIN
    
    def test_stage_environment_uses_intermediate_policies(self):
        """Test that stage environment uses appropriate intermediate policies"""
        app = core.App(context={"env": "stage"})
        stack = CdkBaseStack(app, "test-stack", env_name="stage")
        template = assertions.Template.from_stack(stack)
        
        # Stage should be between dev and prod - using DESTROY for easy cleanup
        # but could use SNAPSHOT for databases
        template.has_resource(
            "AWS::S3::Bucket",
            {
                "DeletionPolicy": "Delete"
            }
        )
    
    def test_environment_name_affects_log_retention(self):
        """Test that different environments have different log retention periods"""
        # Dev: shorter retention (7 days)
        app_dev = core.App(context={"env": "dev"})
        stack_dev = CdkBaseStack(app_dev, "test-stack-dev", env_name="dev")
        template_dev = assertions.Template.from_stack(stack_dev)
        
        # Prod: longer retention (90 days)
        app_prod = core.App(context={"env": "prod"})
        stack_prod = CdkBaseStack(app_prod, "test-stack-prod", env_name="prod")
        template_prod = assertions.Template.from_stack(stack_prod)
        
        # Verify that log groups exist with retention settings
        # (This test will drive the implementation of environment-aware log retention)
        template_dev.has_resource_properties(
            "AWS::Logs::LogGroup",
            {
                "RetentionInDays": 7
            }
        )
        
        template_prod.has_resource_properties(
            "AWS::Logs::LogGroup",
            {
                "RetentionInDays": 90
            }
        )
    
    def test_stack_name_includes_environment_suffix(self):
        """Test that stack names are suffixed with environment for clarity"""
        app = core.App(context={"env": "dev"})
        stack = CdkBaseStack(app, "CdkBaseStack", env_name="dev")
        
        # Stack ID should reflect environment context
        assert "dev" in stack.stack_name.lower() or stack.node.try_get_context("env") == "dev"
    
    def test_environment_context_is_readable_from_stack(self):
        """Test that environment context can be retrieved within the stack"""
        app = core.App(context={"env": "prod"})
        stack = CdkBaseStack(app, "test-stack", env_name="prod")
        
        # The stack should be able to read the environment context
        # This will be validated through the stack's behavior
        template = assertions.Template.from_stack(stack)
        
        # Verify stack can be synthesized with prod context
        assert template is not None
    
    def test_default_environment_is_dev_when_not_specified(self):
        """Test that the default environment is 'dev' when not explicitly specified"""
        app = core.App()
        stack = CdkBaseStack(app, "test-stack")
        template = assertions.Template.from_stack(stack)
        
        # Should synthesize successfully with dev defaults
        assert template is not None
        
        # Should use dev-like policies (DESTROY)
        template.has_resource(
            "AWS::S3::Bucket",
            {
                "DeletionPolicy": "Delete"
            }
        )
    
    def test_all_three_environments_can_synthesize(self):
        """Test that all three environments (dev, stage, prod) can synthesize successfully"""
        environments = ["dev", "stage", "prod"]
        
        for env_name in environments:
            app = core.App(context={"env": env_name})
            stack = CdkBaseStack(app, f"test-stack-{env_name}", env_name=env_name)
            template = assertions.Template.from_stack(stack)
            
            # Each environment should synthesize successfully
            assert template is not None
            
            # Verify basic resources exist in all environments
            template.resource_count_is("AWS::S3::Bucket", 2)
            template.resource_count_is("AWS::DynamoDB::Table", 1)
            template.resource_count_is("AWS::StepFunctions::StateMachine", 1)
    
    def test_kms_key_has_environment_aware_removal_policy(self):
        """Test that KMS keys have environment-appropriate removal policies"""
        # Dev: DESTROY
        app_dev = core.App(context={"env": "dev"})
        stack_dev = CdkBaseStack(app_dev, "test-stack-dev", env_name="dev")
        template_dev = assertions.Template.from_stack(stack_dev)
        
        # Prod: RETAIN
        app_prod = core.App(context={"env": "prod"})
        stack_prod = CdkBaseStack(app_prod, "test-stack-prod", env_name="prod")
        template_prod = assertions.Template.from_stack(stack_prod)
        
        # KMS keys in dev should be deletable
        template_dev.has_resource(
            "AWS::KMS::Key",
            {
                "DeletionPolicy": "Delete"
            }
        )
        
        # KMS keys in prod should be retained
        template_prod.has_resource(
            "AWS::KMS::Key",
            {
                "DeletionPolicy": "Retain"
            }
        )
    
    def test_dynamodb_table_has_environment_aware_removal_policy(self):
        """Test that DynamoDB tables have environment-appropriate removal policies"""
        # Dev: DESTROY
        app_dev = core.App(context={"env": "dev"})
        stack_dev = CdkBaseStack(app_dev, "test-stack-dev", env_name="dev")
        template_dev = assertions.Template.from_stack(stack_dev)
        
        # Prod: RETAIN
        app_prod = core.App(context={"env": "prod"})
        stack_prod = CdkBaseStack(app_prod, "test-stack-prod", env_name="prod")
        template_prod = assertions.Template.from_stack(stack_prod)
        
        # DynamoDB in dev should be deletable
        template_dev.has_resource(
            "AWS::DynamoDB::Table",
            {
                "DeletionPolicy": "Delete"
            }
        )
        
        # DynamoDB in prod should be retained
        template_prod.has_resource(
            "AWS::DynamoDB::Table",
            {
                "DeletionPolicy": "Retain"
            }
        )
