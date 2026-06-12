
# Event-Driven Sleep Audio Pipeline

[![CI](https://github.com/obstreperous-ai/cdk-sleep-py-copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/obstreperous-ai/cdk-sleep-py-copilot/actions/workflows/ci.yml)

A production-ready, serverless, event-driven AWS pipeline that ingests audio files, processes them into soothing sleep audio using Amazon Polly, and delivers results with comprehensive metadata tracking and notifications.

> 📐 **Architecture:** See [`ARCHITECTURE.md`](./ARCHITECTURE.md) for the complete system design, Mermaid diagrams, and detailed component descriptions.  
> 🤝 **Contributing:** See [`AGENT_GUIDELINES.md`](./AGENT_GUIDELINES.md) for TDD workflow and contribution guidelines.  
> 📊 **Project Summary:** See [`SUMMARY.md`](./SUMMARY.md) for key decisions and implementation notes.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Deployment](#deployment)
- [Usage](#usage)
- [Testing](#testing)
- [Environment Configuration](#environment-configuration)
- [Monitoring and Observability](#monitoring-and-observability)
- [Project Structure](#project-structure)
- [Development](#development)
- [Troubleshooting](#troubleshooting)

---

## Overview

The **Event-Driven Sleep Audio Pipeline** is a fully serverless AWS solution built with AWS CDK (Python) that automatically processes audio files through a complete workflow:

1. **Upload** audio to S3 Input Bucket
2. **Automatic trigger** via EventBridge on S3 Object Created event
3. **Orchestrated processing** with AWS Step Functions
4. **Audio synthesis** using Amazon Polly (neural voice)
5. **Output storage** in S3 Output Bucket with versioning
6. **Metadata tracking** in DynamoDB with processing status
7. **Notifications** via SNS for success and failure scenarios

The pipeline is designed with **strict TDD** principles, comprehensive error handling, retry policies, and multi-environment support (dev/stage/prod).

---

## Architecture

**High-Level Flow:**

```
User Upload → S3 Input Bucket → EventBridge Rule → Step Functions State Machine
                                                              ↓
                                         ┌─────────────────────┴────────────────────┐
                                         ↓                                          ↓
                                  Lambda Function                           DynamoDB Table
                              (Audio Processing)                         (Metadata Tracking)
                                         ↓                                          ↓
                                  Amazon Polly                            Status Updates
                              (Speech Synthesis)                                   ↓
                                         ↓                                  SNS Topics
                                  S3 Output Bucket                    (Success/Failure)
                              (Processed Audio)
```

**Key Components:**

- **S3 Buckets**: Input (raw audio) and Output (processed audio) with encryption and versioning
- **EventBridge Rule**: Detects S3 Object Created events and triggers the state machine
- **Step Functions State Machine**: Orchestrates the complete processing workflow with error handling
- **Lambda Function**: Downloads input audio, synthesizes sleep audio using Polly, uploads to output S3
- **Amazon Polly**: Neural text-to-speech synthesis (Joanna voice)
- **DynamoDB Table**: Tracks processing status and metadata (audioId, status, timestamps, output location)
- **SNS Topics**: Publishes success and failure notifications
- **CloudWatch**: Centralized logging, alarms for critical failures
- **X-Ray**: Distributed tracing for Lambda and Step Functions

For complete architecture details and diagrams, see [ARCHITECTURE.md](./ARCHITECTURE.md).

---

## Features

✅ **Fully Serverless & Event-Driven** - No servers to manage, scales automatically  
✅ **Production-Ready Error Handling** - Exponential backoff retries, comprehensive error paths  
✅ **Multi-Environment Support** - Separate dev/stage/prod configurations with context switching  
✅ **Observability Built-In** - CloudWatch Logs, alarms, X-Ray tracing, structured JSON logging  
✅ **Security First** - KMS encryption, private S3 buckets, least-privilege IAM policies  
✅ **TDD from Day One** - 138 comprehensive tests covering infrastructure and Lambda functions  
✅ **Input Validation** - Strict validation for file formats (.mp3, .wav, .m4a, .ogg, .flac)  
✅ **Output Tracking** - DynamoDB metadata records include output location, size, and timestamps  
✅ **CI/CD Ready** - GitHub Actions workflow for automated testing and CDK synthesis

---

## Prerequisites

- **AWS Account** with appropriate permissions for CDK deployments
- **AWS CLI** configured with credentials (`aws configure`)
- **Python 3.12+** installed
- **Node.js 18+** and npm (for AWS CDK CLI)
- **AWS CDK CLI** v2.x installed (`npm install -g aws-cdk@2`)

---

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/obstreperous-ai/cdk-sleep-py-copilot.git
cd cdk-sleep-py-copilot
```

### 2. Set Up Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate.bat  # Windows
```

### 3. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 4. Synthesize CloudFormation Template

```bash
cdk synth
```

### 5. Run Tests

```bash
pytest -v
```

---

## Deployment

### Deploy to Development Environment (Default)

```bash
cdk deploy
# or explicitly:
cdk deploy -c env=dev
```

### Deploy to Staging Environment

```bash
cdk deploy -c env=stage
```

### Deploy to Production Environment

```bash
cdk deploy -c env=prod
```

### First-Time Deployment (Bootstrap)

If deploying to a new AWS account/region, bootstrap CDK first:

```bash
cdk bootstrap aws://ACCOUNT-ID/REGION
```

### View Deployment Diff

```bash
cdk diff
# or for specific environment:
cdk diff -c env=prod
```

### Destroy Stack

```bash
cdk destroy
# or for specific environment:
cdk destroy -c env=prod
```

---

## Usage

### Upload Audio for Processing

Once deployed, you can upload audio files to the Input S3 bucket to trigger processing:

**Using AWS CLI:**

```bash
# Get the Input Bucket name from CloudFormation outputs
BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name CdkBaseStack-dev \
  --query "Stacks[0].Outputs[?OutputKey=='InputBucketName'].OutputValue" \
  --output text)

# Upload an audio file
aws s3 cp your-audio-file.mp3 s3://${BUCKET_NAME}/raw/user123/recording001.mp3
```

**Using AWS Console:**

1. Navigate to S3 Console
2. Find the Input Bucket (`CdkBaseStack-dev-SleepAudioInputBucket-...`)
3. Upload an audio file (supported formats: .mp3, .wav, .m4a, .ogg, .flac)

### Monitor Processing

**Check Step Functions Execution:**

1. Navigate to AWS Step Functions Console
2. Select `SleepAudioPipelineStateMachine`
3. View execution status and logs

**Check DynamoDB Metadata:**

```bash
# Get the DynamoDB table name
TABLE_NAME=$(aws cloudformation describe-stacks \
  --stack-name CdkBaseStack-dev \
  --query "Stacks[0].Outputs[?OutputKey=='MetadataTableName'].OutputValue" \
  --output text)

# Query item
aws dynamodb get-item \
  --table-name ${TABLE_NAME} \
  --key '{"audioId": {"S": "raw/user123/recording001.mp3"}}'
```

**View CloudWatch Logs:**

```bash
# Step Functions logs
aws logs tail /aws/vendedlogs/states/SleepAudioPipelineStateMachine --follow

# Lambda logs
aws logs tail /aws/lambda/SleepAudioProcessor --follow
```

### Retrieve Processed Audio

```bash
# Get the Output Bucket name
OUTPUT_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name CdkBaseStack-dev \
  --query "Stacks[0].Outputs[?OutputKey=='OutputBucketName'].OutputValue" \
  --output text)

# Download processed audio
aws s3 cp s3://${OUTPUT_BUCKET}/processed/recording001_20260611_062000.mp3 .
```

---

## Testing

### Run All Tests

```bash
pytest -v
```

### Run Specific Test Files

```bash
# E2E validation tests
pytest tests/unit/test_end_to_end_validation.py -v

# Lambda function tests
pytest tests/unit/test_audio_processing.py -v

# Infrastructure tests
pytest tests/unit/test_cdk_base_stack.py -v
```

### Test Coverage

The project includes **138 comprehensive tests** covering:

- ✅ **23 End-to-End Validation Tests** - Complete pipeline flow, error handling, retry behavior
- ✅ **51 Infrastructure Tests** - CDK resource creation, IAM policies, permissions
- ✅ **19 Pipeline Integration Tests** - Component integration, EventBridge → Step Functions → Lambda
- ✅ **8 Lambda Validation Tests** - Input validation, error handling
- ✅ **7 Audio Processing Tests** - S3 operations, Polly synthesis, output generation
- ✅ **12 Multi-Environment Tests** - Dev/stage/prod configuration
- ✅ **13 Error Handling & Observability Tests** - Retry policies, X-Ray, CloudWatch alarms
- ✅ **5 Pipeline Construct Tests** - CI/CD pipeline stack

---

## Environment Configuration

The pipeline supports three environments with different configurations:

### Development (`dev`)

```bash
cdk deploy -c env=dev
```

- **Removal Policy**: DESTROY (resources deleted on stack deletion)
- **S3 Auto-Delete**: Enabled (buckets emptied on deletion)
- **Log Retention**: 7 days
- **Use Case**: Local testing, experimentation

### Staging (`stage`)

```bash
cdk deploy -c env=stage
```

- **Removal Policy**: DESTROY
- **S3 Auto-Delete**: Enabled
- **Log Retention**: 30 days
- **Use Case**: Pre-production testing

### Production (`prod`)

```bash
cdk deploy -c env=prod
```

- **Removal Policy**: RETAIN (resources preserved on stack deletion)
- **S3 Auto-Delete**: Disabled (manual deletion required)
- **Log Retention**: 90 days
- **Use Case**: Production workloads

---

## Monitoring and Observability

### CloudWatch Alarms

The pipeline includes CloudWatch alarms for critical failures:

1. **State Machine Execution Failures**
   - Metric: `ExecutionsFailed`
   - Threshold: ≥ 1 failures in 5 minutes
   - Action: Publishes to Failure SNS topic

2. **Lambda Function Errors**
   - Metric: `Errors`
   - Threshold: ≥ 1 errors in 5 minutes
   - Action: Publishes to Failure SNS topic

### X-Ray Tracing

Distributed tracing is enabled for:
- **Step Functions State Machine** - Complete execution trace
- **Lambda Function** - Function execution and AWS SDK calls

View traces in AWS X-Ray Console.

### Structured Logging

Lambda function uses structured JSON logging:

```json
{
  "timestamp": "2026-06-11T06:20:00.000Z",
  "level": "INFO",
  "message": "Processing completed successfully",
  "request_id": "abc123",
  "audio_id": "raw/user123/recording001.mp3",
  "status": "success"
}
```

---

## Project Structure

```
cdk-sleep-py-copilot/
├── app.py                      # CDK app entry point
├── cdk.json                    # CDK configuration
├── cdk_base/
│   ├── __init__.py
│   ├── cdk_base_stack.py      # Main infrastructure stack
│   └── pipeline_stack.py      # CI/CD pipeline stack
├── lambda/
│   └── audio_processor.py     # Lambda function handler
├── tests/
│   └── unit/
│       ├── test_end_to_end_validation.py
│       ├── test_cdk_base_stack.py
│       ├── test_audio_processing.py
│       ├── test_lambda_validation.py
│       ├── test_pipeline_integration.py
│       ├── test_error_handling_observability.py
│       ├── test_multi_environment.py
│       └── test_pipeline_construct.py
├── .github/
│   └── workflows/
│       └── ci.yml             # GitHub Actions CI workflow
├── ARCHITECTURE.md            # Complete architecture documentation
├── AGENT_GUIDELINES.md        # TDD and contribution guidelines
├── SUMMARY.md                 # Project summary and key decisions
├── README.md                  # This file
├── requirements.txt           # Python dependencies
└── requirements-dev.txt       # Development dependencies
```

---

## Development

### Following TDD Workflow

This project follows strict Test-Driven Development:

1. **Write failing test first** in `tests/unit/`
2. **Run test** - verify it fails: `pytest tests/unit/test_your_feature.py`
3. **Implement minimal code** in `cdk_base/` or `lambda/`
4. **Run test** - verify it passes
5. **Refactor** while keeping tests green
6. **Run all tests** - ensure no regressions: `pytest -v`

See [AGENT_GUIDELINES.md](./AGENT_GUIDELINES.md) for complete workflow.

### Running CI Checks Locally

```bash
# Run all CI checks
pytest                  # Run tests
cdk synth               # Synthesize CloudFormation
cdk diff --template cdk.out/CdkBaseStack.template.json  # Verify diff
```

### Adding New Features

1. Create failing tests in `tests/unit/`
2. Implement feature in `cdk_base/cdk_base_stack.py` or `lambda/audio_processor.py`
3. Update `ARCHITECTURE.md` if design changes
4. Ensure all tests pass: `pytest -v`
5. Update documentation (README, ARCHITECTURE, etc.)

---

## Troubleshooting

### Common Issues

**Issue: `cdk synth` fails with "jsii" errors**

```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

**Issue: Tests fail with import errors**

```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Install dev dependencies
pip install -r requirements-dev.txt
```

**Issue: Deployment fails with "insufficient permissions"**

- Verify AWS credentials: `aws sts get-caller-identity`
- Ensure IAM user/role has CDK deployment permissions
- Check if CDK bootstrap is required: `cdk bootstrap`

**Issue: Lambda function validation errors**

- Supported formats: `.mp3`, `.wav`, `.m4a`, `.ogg`, `.flac`
- Check file extension matches supported list
- Verify S3 event structure includes `detail.bucket.name` and `detail.object.key`

**Issue: Step Functions execution fails**

- Check CloudWatch Logs: `/aws/vendedlogs/states/SleepAudioPipelineStateMachine`
- Review error details in Step Functions Console
- Verify Lambda function has necessary permissions (S3, Polly, DynamoDB)

**Issue: Output audio not generated**

- Check Lambda logs: `/aws/lambda/SleepAudioProcessor`
- Verify Polly permissions in Lambda execution role
- Ensure output bucket exists and Lambda has write permissions

---

## Additional Resources

- **AWS CDK Documentation**: https://docs.aws.amazon.com/cdk/
- **AWS Step Functions**: https://docs.aws.amazon.com/step-functions/
- **Amazon Polly**: https://docs.aws.amazon.com/polly/
- **AWS Lambda**: https://docs.aws.amazon.com/lambda/
- **Project Issues**: https://github.com/obstreperous-ai/cdk-sleep-py-copilot/issues

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

Built with **strict TDD** principles using **GitHub Copilot** as the Senior AWS CDK TDD Specialist.

**Development Timeline** (Issues #2-#12):
- Issue #2: Architecture design baseline
- Issue #3: Core S3 Buckets + EventBridge Rule
- Issue #4: Step Functions State Machine + Polly Integration
- Issue #5: DynamoDB Metadata Table + I/O Handling
- Issue #6: SNS Notifications + Error Handling
- Issue #7: Lambda Function Skeleton + Integration
- Issue #8: Complete Pipeline Wiring + Input Validation
- Issue #9: Pipeline Testing + Deployment Preparation
- Issue #10: Advanced Error Handling + Observability
- Issue #11: Full Audio Processing + Output Handling
- Issue #12: End-to-End Validation + Documentation Polish

---

**Status**: ✅ **Production Ready** - Complete implementation with 138 passing tests, comprehensive documentation, and multi-environment support.
