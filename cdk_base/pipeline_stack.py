"""
CDK Pipeline Stack (Issue #9)

This is a skeleton implementation of a CDK Pipeline for CI/CD deployment.
It provides basic structure for deploying the application stack to multiple environments.
"""
from aws_cdk import (
    Stack,
    Stage,
    pipelines,
    aws_codecommit as codecommit,
    aws_codebuild as codebuild,
)
from constructs import Construct
from typing import List, Optional

from cdk_base.cdk_base_stack import CdkBaseStack


class PipelineStack(Stack):
    """
    CDK Pipeline for deploying the Sleep Audio Pipeline application.
    
    This is a skeleton implementation that provides:
    - Source stage (GitHub connection ready)
    - Synth stage (CDK synthesis)
    - Multi-environment deployment capability
    
    Future enhancements will add:
    - Actual GitHub source integration
    - Testing stages
    - Approval gates for production
    - Blue/green deployments
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        repo_owner: str = "obstreperous-ai",
        repo_name: str = "cdk-sleep-py-copilot",
        branch: str = "main",
        deploy_environments: Optional[List[str]] = None,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.template_options.description = "CDK Pipeline for Sleep Audio Pipeline deployment"

        # Store configuration
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.branch = branch
        self.deploy_environments = deploy_environments or ["dev"]

        # Create a basic pipeline structure
        # Note: This is a skeleton implementation
        # A full GitHub source integration would require:
        # 1. GitHub connection setup
        # 2. OAuth tokens or GitHub App credentials
        # 3. Webhook configuration
        
        # For the skeleton, we'll create a placeholder CodeCommit repository
        # In production, this would be replaced with GitHub source
        # NOTE: This creates a real CodeCommit repo during testing. To clean up:
        #   aws codecommit delete-repository --repository-name <repo-name>
        placeholder_repo = codecommit.Repository(
            self,
            "PlaceholderRepo",
            repository_name=f"{repo_name}-pipeline-placeholder",
            description="Placeholder repository for pipeline skeleton (replace with GitHub in production)",
        )
        
        # Create the synth step (builds and synthesizes the CDK app)
        synth_step = pipelines.CodeBuildStep(
            "Synth",
            # Use the placeholder repo as input for skeleton
            input=pipelines.CodePipelineSource.code_commit(
                repository=placeholder_repo,
                branch=branch,
            ),
            commands=[
                "npm install -g aws-cdk",
                "pip install -r requirements.txt",
                "pip install -r requirements-dev.txt",
                "pytest",  # Run tests during synthesis
                "cdk synth",
            ],
            primary_output_directory="cdk.out",
        )

        # Create the pipeline
        self.pipeline = pipelines.CodePipeline(
            self,
            "Pipeline",
            synth=synth_step,
            # Enable Docker for any container-based constructs
            docker_enabled_for_synth=True,
            # Cross-account deployment support
            cross_account_keys=True,
        )

        # Add deployment stages for each environment
        for env_name in self.deploy_environments:
            self._add_application_stage(env_name)

    def _add_application_stage(self, env_name: str) -> None:
        """
        Add a deployment stage for the specified environment.
        
        Args:
            env_name: Environment name (dev, stage, prod)
        """
        # Create an application stage
        app_stage = ApplicationStage(
            self,
            f"Deploy-{env_name.capitalize()}",
            env_name=env_name,
        )

        # Add the stage to the pipeline
        # In a full implementation, prod would have manual approval gates
        self.pipeline.add_stage(app_stage)


class ApplicationStage(Stage):
    """
    Application stage that deploys the main application stack.
    
    This represents one deployment environment (dev, stage, or prod).
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        env_name: str = "dev",
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Deploy the main application stack for this environment
        CdkBaseStack(
            self,
            f"CdkBaseStack-{env_name}",
            env_name=env_name,
        )
