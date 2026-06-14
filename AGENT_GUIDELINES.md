# Agent & Contributor Guidelines

These guidelines apply to every contributor and automation agent working on the
**Event-Driven Sleep Audio Pipeline**.

> **Project Status**: ✅ **Complete** - Production-ready implementation with 138 passing tests, comprehensive documentation, and multi-environment support.

---

## Source of Truth

[`ARCHITECTURE.md`](./ARCHITECTURE.md) is the **single source of truth** for the
system design. Before starting any issue:

1. Read `ARCHITECTURE.md` and ensure your change is consistent with the documented
   data flow, services, and Mermaid diagram.
2. If your change alters the design, **update `ARCHITECTURE.md` (description and
   diagram together) in the same pull request** so the document and the code never
   drift apart.

---

## Test-Driven Development (TDD)

All infrastructure changes follow a strict TDD workflow:

1. **Write a failing test first** under `tests/` using `aws_cdk.assertions`
   (`Template.from_stack(...)`) to assert the resources/properties you expect.
2. **Run the test and watch it fail** (`pytest`).
3. **Implement** the minimal CDK code in `cdk_base/` to make the test pass.
4. **Refactor** while keeping tests green.

**Example TDD Workflow:**

```bash
# 1. Write failing test
# Create test_new_feature.py with assertions for expected resources

# 2. Run test (should fail)
pytest tests/unit/test_new_feature.py -v

# 3. Implement feature in cdk_base/cdk_base_stack.py

# 4. Run test again (should pass)
pytest tests/unit/test_new_feature.py -v

# 5. Run all tests (ensure no regressions)
pytest -v

# 6. Refactor if needed, keeping tests green
```

---

## Validation Commands

Run these locally before opening a pull request (they mirror CI in
[`.github/workflows/ci.yml`](./.github/workflows/ci.yml)):

```bash
# Run all tests (138 comprehensive tests)
pytest -v

# Synthesize CloudFormation template
cdk synth

# Verify CDK diff against synthesized template
cdk diff --template cdk.out/CdkBaseStack.template.json
```

**Expected Results:**
- ✅ All 138 tests pass in ~14 seconds
- ✅ CDK synth completes successfully
- ✅ CDK diff shows no unexpected changes

---

## Scope Discipline

- Keep changes **minimal and focused** on the current issue.
- Do not implement future-issue functionality ahead of time.
- Documentation-only issues (such as the initial architecture design) must not
  modify CDK stack code.

---

## Security & Best Practices

Follow the security baseline in `ARCHITECTURE.md`: private buckets, encryption at
rest and in transit, and least-privilege IAM roles. Never commit secrets.

**Security Checklist:**
- ✅ S3 buckets are private (block all public access)
- ✅ Encryption at rest (S3: AES-256, DynamoDB, SNS: KMS)
- ✅ Encryption in transit (HTTPS for all service communication)
- ✅ Least-privilege IAM policies (scoped to specific resources)
- ✅ KMS key rotation enabled for SNS
- ✅ No hardcoded secrets or credentials in code

---

## Multi-Environment Support

The pipeline supports three environments with distinct configurations:

```bash
# Development (default)
cdk deploy -c env=dev

# Staging
cdk deploy -c env=stage

# Production
cdk deploy -c env=prod
```

**Environment Configurations:**

| Environment | Removal Policy | S3 Auto-Delete | Log Retention | Use Case |
|------------|---------------|----------------|---------------|----------|
| dev | DESTROY | Enabled | 7 days | Local testing, experimentation |
| stage | DESTROY | Enabled | 30 days | Pre-production testing |
| prod | RETAIN | Disabled | 90 days | Production workloads |

---

## Testing Strategy

The project includes **143 comprehensive tests** organized by category:

### Test Files

1. **`test_end_to_end_validation.py`** (23 tests)
   - Complete happy path flow validation
   - Error handling and failure scenarios
   - Retry behavior validation
   - Input validation rejection paths
   - Observability (CloudWatch, X-Ray)
   - Multi-environment synthesis

2. **`test_cdk_base_stack.py`** (51 tests)
   - Infrastructure resource creation (S3, EventBridge, Step Functions, Lambda, DynamoDB, SNS)
   - IAM policies and permissions
   - State machine configuration
   - Component integration
   - Snapshot testing

3. **`test_pipeline_integration.py`** (19 tests)
   - S3 → EventBridge → Step Functions integration
   - Lambda integration with state machine
   - DynamoDB status updates
   - SNS notification triggers

4. **`test_lambda_validation.py`** (8 tests)
   - Input validation (missing fields, empty values)
   - File format validation (supported/unsupported extensions)

5. **`test_audio_processing.py`** (12 tests)
   - S3 download/upload operations
   - Polly synthesis integration
   - Output metadata generation
   - Error handling (S3, Polly failures)
   - Logging edge cases (WARN, DEBUG)
   - Client factory functions

6. **`test_error_handling_observability.py`** (13 tests)
   - Retry policies (Lambda, Polly, DynamoDB)
   - Error-specific catch blocks
   - X-Ray tracing configuration
   - CloudWatch alarms

7. **`test_multi_environment.py`** (12 tests)
   - Environment-specific removal policies
   - S3 auto-delete configuration
   - Log retention periods

8. **`test_pipeline_construct.py`** (5 tests)
   - CI/CD pipeline stack creation
   - GitHub source integration

### Running Tests

```bash
# Run all tests
pytest -v

# Run specific test file
pytest tests/unit/test_end_to_end_validation.py -v

# Run specific test class
pytest tests/unit/test_end_to_end_validation.py::TestEndToEndHappyPath -v

# Run specific test method
pytest tests/unit/test_end_to_end_validation.py::TestEndToEndHappyPath::test_complete_pipeline_has_required_resources -v
```

---

## Project Structure

```
cdk-sleep-py-copilot/
├── app.py                      # CDK app entry point (env context handling)
├── cdk.json                    # CDK configuration
├── cdk_base/
│   ├── __init__.py
│   ├── cdk_base_stack.py      # Main infrastructure stack (all resources)
│   └── pipeline_stack.py      # CI/CD pipeline stack
├── lambda/
│   └── audio_processor.py     # Lambda function (validation, Polly, S3 operations)
├── tests/
│   └── unit/                  # All test files (138 tests)
├── .github/
│   └── workflows/
│       └── ci.yml             # GitHub Actions CI workflow
├── ARCHITECTURE.md            # Complete architecture documentation (single source of truth)
├── AGENT_GUIDELINES.md        # This file (TDD workflow, contribution guidelines)
├── SUMMARY.md                 # Project summary (key decisions, metrics, lessons learned)
├── README.md                  # User-facing documentation (deployment, usage, troubleshooting)
├── requirements.txt           # Python dependencies (CDK, boto3)
└── requirements-dev.txt       # Development dependencies (pytest)
```

---

## Common Development Tasks

### Adding a New CDK Resource

```bash
# 1. Write test first
# Create test in tests/unit/test_cdk_base_stack.py

# 2. Run test (should fail)
pytest tests/unit/test_cdk_base_stack.py::test_your_new_resource -v

# 3. Add resource to cdk_base/cdk_base_stack.py

# 4. Run test again (should pass)
pytest tests/unit/test_cdk_base_stack.py::test_your_new_resource -v

# 5. Update ARCHITECTURE.md with new resource description
```

### Modifying Lambda Function

```bash
# 1. Write test first in tests/unit/test_audio_processing.py

# 2. Run test (should fail)
pytest tests/unit/test_audio_processing.py::test_your_new_functionality -v

# 3. Modify lambda/audio_processor.py

# 4. Run test again (should pass)
pytest tests/unit/test_audio_processing.py::test_your_new_functionality -v

# 5. Run all tests to ensure no regressions
pytest -v
```

### Adding Environment-Specific Configuration

```bash
# 1. Add configuration in cdk_base/cdk_base_stack.py (env_name parameter)

# 2. Add test in tests/unit/test_multi_environment.py

# 3. Verify all environments synthesize
cdk synth -c env=dev
cdk synth -c env=stage
cdk synth -c env=prod

# 4. Update ARCHITECTURE.md with new configuration details
```

---

## Continuous Integration

The project uses GitHub Actions for CI (`.github/workflows/ci.yml`):

```yaml
# CI workflow runs on:
# - Every pull request
# - Every push to main

# CI steps:
1. Checkout code
2. Set up Python 3.12
3. Set up Node.js 22
4. Install Python dependencies (requirements.txt, requirements-dev.txt)
5. Install AWS CDK CLI v2
6. Run pytest (all 138 tests)
7. Run cdk synth
8. Run cdk diff (validation)
```

**All CI checks must pass before merging.**

---

## Deployment Best Practices

### First-Time Deployment

```bash
# 1. Bootstrap CDK (one-time per account/region)
cdk bootstrap aws://ACCOUNT-ID/REGION

# 2. Synthesize and review changes
cdk synth -c env=dev
cdk diff -c env=dev

# 3. Deploy to dev environment
cdk deploy -c env=dev

# 4. Test deployment
# Upload test audio file to Input S3 bucket
# Monitor Step Functions execution
# Verify output in Output S3 bucket
# Check DynamoDB metadata record
```

### Production Deployment

```bash
# 1. Ensure all tests pass
pytest -v

# 2. Review production configuration
cdk synth -c env=prod

# 3. Review changes (should be minimal if already deployed to stage)
cdk diff -c env=prod

# 4. Deploy to production
cdk deploy -c env=prod

# 5. Monitor CloudWatch alarms and logs
```

---

## Troubleshooting

### Tests Fail

```bash
# 1. Ensure virtual environment is activated
source .venv/bin/activate

# 2. Install/update dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 3. Run specific failing test for more details
pytest tests/unit/test_file.py::test_name -v -s

# 4. Check for code changes that broke assumptions
```

### CDK Synth Fails

```bash
# 1. Check Python version (requires 3.12+)
python --version

# 2. Reinstall dependencies
pip install --upgrade -r requirements.txt

# 3. Check CDK version (requires v2.x)
cdk --version

# 4. Review error message for specific resource issues
```

### Deployment Fails

```bash
# 1. Verify AWS credentials
aws sts get-caller-identity

# 2. Check IAM permissions (requires CDK deployment permissions)

# 3. Verify CDK bootstrap completed
# Should see CDKToolkit stack in CloudFormation

# 4. Review CloudFormation events in AWS Console for specific errors
```

---

## Code Style

### Python

- Follow PEP 8 style guide
- Use type hints for all function signatures
- Write docstrings for all classes and functions
- Use descriptive variable names
- Keep functions small and focused

### CDK

- Use L2 constructs when available
- Group related resources together
- Use descriptive construct IDs
- Add comments for complex configurations
- Follow least-privilege IAM principles

### Lambda

- Use structured JSON logging (`log_structured()` helper)
- Implement input validation in separate function
- Return structured responses with status, message, and data
- Handle all exceptions gracefully
- Include request_id in all log messages

---

## Documentation Standards

When updating documentation:

1. **README.md**: User-facing, deployment, usage, troubleshooting
2. **ARCHITECTURE.md**: System design, single source of truth, technical details
3. **SUMMARY.md**: Key decisions, metrics, lessons learned, experiment notes
4. **AGENT_GUIDELINES.md**: TDD workflow, contribution process, development tasks

**Keep all documentation synchronized with code changes.**

---

## Additional Resources

- **AWS CDK Documentation**: https://docs.aws.amazon.com/cdk/
- **AWS Step Functions**: https://docs.aws.amazon.com/step-functions/
- **Amazon Polly**: https://docs.aws.amazon.com/polly/
- **pytest Documentation**: https://docs.pytest.org/
- **GitHub Actions**: https://docs.github.com/actions

---

## Project History

**Development Timeline (Issues #2-#12):**

- **Issue #2**: Architecture design baseline (documentation only)
- **Issue #3**: Core S3 Buckets + EventBridge Rule (10 tests)
- **Issue #4**: Step Functions State Machine + Polly Integration (15 tests)
- **Issue #5**: DynamoDB Metadata Table + I/O Handling (20 tests)
- **Issue #6**: SNS Notifications + Error Handling (25 tests)
- **Issue #7**: Lambda Function Skeleton + Integration (30 tests)
- **Issue #8**: Complete Pipeline Wiring + Input Validation (38 tests)
- **Issue #9**: Pipeline Testing + Deployment Preparation (46 tests)
- **Issue #10**: Advanced Error Handling + Observability (58 tests)
- **Issue #11**: Full Audio Processing + Output Handling (115 tests)
- **Issue #12**: End-to-End Validation + Documentation Polish (138 tests)

**Final Status**: ✅ **Production Ready** - Complete implementation following strict TDD methodology.

---

**Built with strict TDD principles using GitHub Copilot as the Senior AWS CDK TDD Specialist.**
