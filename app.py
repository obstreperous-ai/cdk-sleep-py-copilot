#!/usr/bin/env python3
import os

import aws_cdk as cdk

from cdk_base.cdk_base_stack import CdkBaseStack


app = cdk.App()

# Get environment from context (e.g., cdk deploy -c env=prod)
# Default to 'dev' if not specified
env_name = app.node.try_get_context("env") or "dev"

# Validate environment name
valid_environments = ["dev", "stage", "prod"]
if env_name not in valid_environments:
    raise ValueError(
        f"Invalid environment '{env_name}'. "
        f"Must be one of: {', '.join(valid_environments)}"
    )

# Create stack with environment-specific configuration
stack_name = f"CdkBaseStack-{env_name}"
CdkBaseStack(
    app, 
    stack_name,
    env_name=env_name,
    # Environment configuration can be added here
    # For example:
    # env=cdk.Environment(
    #     account=os.getenv('CDK_DEFAULT_ACCOUNT'),
    #     region=os.getenv('CDK_DEFAULT_REGION')
    # ),
)

app.synth()
