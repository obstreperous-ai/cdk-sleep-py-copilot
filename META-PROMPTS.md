# Meta-Prompts & Reusable Agent Patterns

**Purpose**: This document extracts reusable meta-prompting patterns and agent guidelines from the Event-Driven Sleep Audio Pipeline project. These patterns can be used as templates for future agentic TDD Infrastructure as Code (IaC) projects.

> 📋 **Reference Project**: This is based on `obstreperous-ai/cdk-sleep-py-copilot`, a production-ready serverless audio processing pipeline built entirely using strict TDD with GitHub Copilot.

---

## Table of Contents

- [Meta-Prompting Philosophy](#meta-prompting-philosophy)
- [Core Patterns](#core-patterns)
  - [Pattern 1: Single Source of Truth](#pattern-1-single-source-of-truth)
  - [Pattern 2: Strict TDD Workflow](#pattern-2-strict-tdd-workflow)
  - [Pattern 3: Scope Discipline](#pattern-3-scope-discipline)
  - [Pattern 4: Documentation Synchronization](#pattern-4-documentation-synchronization)
  - [Pattern 5: Multi-Environment Context](#pattern-5-multi-environment-context)
  - [Pattern 6: Validation Commands](#pattern-6-validation-commands)
- [Agent Instruction Templates](#agent-instruction-templates)
  - [New Feature Development](#new-feature-development)
  - [Bug Fix](#bug-fix)
  - [Documentation Update](#documentation-update)
  - [Security Enhancement](#security-enhancement)
- [Testing Patterns](#testing-patterns)
- [Security Patterns](#security-patterns)
- [Observability Patterns](#observability-patterns)
- [Best Practices](#best-practices)

---

## Meta-Prompting Philosophy

**Core Principle**: Agent-driven development succeeds when the agent has clear, unambiguous instructions, a single source of truth, and strict discipline around scope and testing.

### Key Concepts

1. **Single Source of Truth** - One authoritative document (e.g., ARCHITECTURE.md) that defines the system design. All code must align with this document.

2. **Test-First Always** - Write failing tests before implementation. This prevents scope creep and ensures every feature is testable.

3. **Scope Discipline** - Agents must focus on one issue at a time, avoiding "helpful" additions that weren't requested.

4. **Documentation as Code** - Documentation must be updated in the same PR as code changes to prevent drift.

5. **Validation Before Merge** - All changes must pass validation commands (tests, synth, diff) before being merged.

---

## Core Patterns

### Pattern 1: Single Source of Truth

**Problem**: Without a clear authority, agents make inconsistent decisions and implementations drift.

**Solution**: Designate one document as the architectural source of truth.

**Template**:

```markdown
## Source of Truth

[`ARCHITECTURE.md`](./ARCHITECTURE.md) is the **single source of truth** for the
system design. Before starting any issue:

1. Read `ARCHITECTURE.md` and ensure your change is consistent with the documented
   data flow, services, and diagrams.
2. If your change alters the design, **update `ARCHITECTURE.md` (description and
   diagram together) in the same pull request** so the document and the code never
   drift apart.
```

**Agent Instruction**:
```
Before implementing, review ARCHITECTURE.md to ensure consistency with the documented design. If your changes modify the architecture, update both the description and diagrams in ARCHITECTURE.md within the same PR.
```

---

### Pattern 2: Strict TDD Workflow

**Problem**: Without TDD discipline, code coverage suffers and bugs slip through.

**Solution**: Enforce a strict test-first workflow for all infrastructure and code changes.

**Template**:

```markdown
## Test-Driven Development (TDD)

All infrastructure changes follow a strict TDD workflow:

1. **Write a failing test first** under `tests/` using your testing framework
2. **Run the test and watch it fail** (confirm the test is valid)
3. **Implement** the minimal code to make the test pass
4. **Run the test** - verify it passes
5. **Refactor** while keeping tests green
6. **Run all tests** - ensure no regressions

**Example Workflow:**

```bash
# 1. Write failing test
# Create test_new_feature.py with assertions

# 2. Run test (should fail)
pytest tests/unit/test_new_feature.py -v

# 3. Implement feature
# Edit source files to make test pass

# 4. Run test again (should pass)
pytest tests/unit/test_new_feature.py -v

# 5. Run all tests (ensure no regressions)
pytest -v
```
```

**Agent Instruction**:
```
Follow strict TDD:
1. Write a failing test first in tests/unit/
2. Run test to confirm it fails
3. Implement minimal code to pass the test
4. Run test to confirm it passes
5. Run all tests to ensure no regressions
Do not implement any code before writing the test.
```

---

### Pattern 3: Scope Discipline

**Problem**: Agents often implement "obvious next steps" or "helpful improvements" beyond the current issue scope.

**Solution**: Explicitly constrain agent scope to the current issue only.

**Template**:

```markdown
## Scope Discipline

- Keep changes **minimal and focused** on the current issue.
- Do not implement future-issue functionality ahead of time.
- Documentation-only issues must not modify source code.
- If you identify improvements outside the issue scope, note them for future issues instead of implementing them.
```

**Agent Instruction**:
```
IMPORTANT: Only implement what is explicitly requested in this issue. Do not:
- Add features from future issues
- Refactor unrelated code
- Implement "obvious improvements" not in scope
If you see opportunities for improvement, document them in a comment but do not implement them.
```

---

### Pattern 4: Documentation Synchronization

**Problem**: Documentation and code drift apart when not updated together.

**Solution**: Require documentation updates in the same PR as code changes.

**Template**:

```markdown
## Documentation Standards

When updating code:

1. **ARCHITECTURE.md**: Update if design/data flow changes
2. **README.md**: Update if user-facing behavior changes
3. **AGENT_GUIDELINES.md**: Update if development workflow changes
4. **Code comments**: Update if implementation logic changes

**Keep all documentation synchronized with code changes.**
```

**Agent Instruction**:
```
Documentation Checklist:
- [ ] Updated ARCHITECTURE.md if design changed
- [ ] Updated README.md if user behavior changed
- [ ] Updated relevant code comments
- [ ] Verified all links still work
All documentation updates must be in the same PR as code changes.
```

---

### Pattern 5: Multi-Environment Context

**Problem**: Different environments (dev/stage/prod) need different configurations but share the same codebase.

**Solution**: Use context parameters for environment-specific configuration.

**Template**:

```markdown
## Multi-Environment Support

The project supports multiple environments with distinct configurations:

```bash
# Development (default)
cdk deploy -c env=dev

# Staging
cdk deploy -c env=stage

# Production
cdk deploy -c env=prod
```

**Environment Configurations:**

| Environment | Removal Policy | Auto-Delete | Log Retention | Use Case |
|------------|---------------|-------------|---------------|----------|
| dev | DESTROY | Enabled | 7 days | Local testing |
| stage | DESTROY | Enabled | 30 days | Pre-prod testing |
| prod | RETAIN | Disabled | 90 days | Production |
```

**Agent Instruction**:
```
When implementing environment-specific behavior:
1. Read env_name parameter from stack constructor
2. Use conditional logic for environment-specific settings
3. Test all environments synthesize successfully:
   cdk synth -c env=dev
   cdk synth -c env=stage
   cdk synth -c env=prod
4. Add tests in tests/unit/test_multi_environment.py
```

---

### Pattern 6: Validation Commands

**Problem**: Without standardized validation, PRs may break existing functionality.

**Solution**: Define and enforce validation commands that mirror CI.

**Template**:

```markdown
## Validation Commands

Run these locally before opening a pull request (they mirror CI):

```bash
# Run all tests
pytest -v

# Synthesize CloudFormation template
cdk synth

# Verify CDK diff
cdk diff --template cdk.out/StackName.template.json
```

**Expected Results:**
- ✅ All tests pass
- ✅ CDK synth completes successfully
- ✅ CDK diff shows no unexpected changes
```

**Agent Instruction**:
```
Before submitting PR, run validation commands:
1. pytest -v (all tests must pass)
2. cdk synth (must complete successfully)
3. cdk diff --template cdk.out/StackName.template.json (review changes)
Report any failures and fix before proceeding.
```

---

## Agent Instruction Templates

### New Feature Development

```markdown
**Task**: Implement [feature name]

**Context**:
- Review ARCHITECTURE.md for design constraints
- This feature is part of Issue #[N]
- Related components: [list components]

**Requirements**:
1. Follow strict TDD workflow (test first)
2. Update ARCHITECTURE.md if design changes
3. Keep changes minimal and focused
4. Ensure all validation commands pass

**Steps**:
1. Write failing test in tests/unit/test_[feature].py
2. Implement minimal code in [source files]
3. Run test to verify it passes
4. Run all tests to ensure no regressions
5. Update documentation if needed
6. Run validation commands

**Success Criteria**:
- [ ] Tests pass (pytest -v)
- [ ] CDK synth succeeds
- [ ] Documentation updated
- [ ] No scope creep
```

---

### Bug Fix

```markdown
**Task**: Fix [bug description]

**Context**:
- Bug report: [description]
- Affected components: [list]
- Expected behavior: [description]
- Actual behavior: [description]

**Requirements**:
1. Write test that reproduces the bug (should fail)
2. Fix the bug with minimal changes
3. Verify test now passes
4. Ensure no regressions

**Steps**:
1. Write failing test demonstrating the bug
2. Run test to confirm it fails
3. Implement fix
4. Run test to verify it passes
5. Run all tests to ensure no regressions
6. Update documentation if behavior changed

**Success Criteria**:
- [ ] Reproduction test added and passes
- [ ] All existing tests still pass
- [ ] Fix is minimal and focused
- [ ] Documentation updated if needed
```

---

### Documentation Update

```markdown
**Task**: Update documentation for [topic]

**Context**:
- Documentation type: [README/ARCHITECTURE/GUIDELINES]
- Reason for update: [describe]
- Related code changes: [if any]

**Requirements**:
1. Keep consistent with existing documentation style
2. Update table of contents if needed
3. Verify all links work
4. Do not modify code unless explicitly required

**Steps**:
1. Review existing documentation
2. Make updates following existing style
3. Update TOC if structure changed
4. Verify all internal links work
5. Check for consistency with code

**Success Criteria**:
- [ ] Documentation is clear and accurate
- [ ] All links work
- [ ] Consistent with existing style
- [ ] No unintended code changes
```

---

### Security Enhancement

```markdown
**Task**: Implement [security feature]

**Context**:
- Security concern: [description]
- Affected components: [list]
- Security baseline: [reference ARCHITECTURE.md]

**Requirements**:
1. Follow security checklist from ARCHITECTURE.md
2. Implement with least-privilege principle
3. Add tests for security configuration
4. Document security rationale

**Security Checklist**:
- [ ] S3 buckets are private
- [ ] Encryption at rest enabled
- [ ] Encryption in transit enabled
- [ ] Least-privilege IAM policies
- [ ] No hardcoded secrets
- [ ] KMS key rotation enabled (if applicable)

**Steps**:
1. Write tests for security configuration
2. Implement security feature
3. Verify tests pass
4. Run all tests for regressions
5. Update security documentation

**Success Criteria**:
- [ ] Security tests pass
- [ ] All checklist items verified
- [ ] Documentation updated
- [ ] No secrets in code
```

---

## Testing Patterns

### Infrastructure Testing (CDK)

```python
# Test pattern for CDK resource creation
def test_resource_exists_with_required_properties():
    """Test that resource exists with correct configuration."""
    template = Template.from_stack(stack)
    
    template.resource_count_is("AWS::ServiceName::Resource", 1)
    
    template.has_resource_properties("AWS::ServiceName::Resource", {
        "PropertyName": "ExpectedValue",
        "ConfigProperty": {
            "Enabled": True
        }
    })
```

### Lambda Function Testing

```python
# Test pattern for Lambda handler
def test_handler_successful_execution():
    """Test Lambda handler happy path."""
    event = {
        "detail": {
            "bucket": {"name": "test-bucket"},
            "object": {"key": "test-file.mp3"}
        }
    }
    
    response = handler(event, {})
    
    assert response["status"] == "success"
    assert "outputKey" in response
```

### Integration Testing

```python
# Test pattern for component integration
def test_eventbridge_triggers_step_functions():
    """Test EventBridge rule targets Step Functions."""
    template = Template.from_stack(stack)
    
    template.has_resource("AWS::Events::Rule", {
        "Properties": {
            "State": "ENABLED",
            "Targets": [
                {
                    "Arn": {"Fn::GetAtt": Match.any_value()},
                    "RoleArn": Match.any_value()
                }
            ]
        }
    })
```

---

## Security Patterns

### Least-Privilege IAM Pattern

```python
# Pattern for least-privilege IAM policies
lambda_role.add_to_policy(iam.PolicyStatement(
    actions=["s3:GetObject"],  # Specific action only
    resources=[
        f"{input_bucket.bucket_arn}/*"  # Specific resource only
    ]
))
```

### Encryption Pattern

```python
# Pattern for encryption at rest
bucket = s3.Bucket(self, "SecureBucket",
    encryption=s3.BucketEncryption.S3_MANAGED,  # AES-256
    enforce_ssl=True,  # Encryption in transit
    block_public_access=s3.BlockPublicAccess.BLOCK_ALL  # Private
)

# Pattern for KMS encryption
kms_key = kms.Key(self, "EncryptionKey",
    enable_key_rotation=True  # Automatic rotation
)

topic = sns.Topic(self, "SecureTopic",
    master_key=kms_key  # KMS encryption
)
```

### Input Validation Pattern

```python
# Pattern for Lambda input validation
class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass

def validate_input(event: Dict[str, Any]) -> None:
    """Validate event structure and content."""
    if "detail" not in event:
        raise ValidationError("Missing 'detail' field in event")
    
    detail = event["detail"]
    if not detail.get("bucket", {}).get("name"):
        raise ValidationError("Missing bucket name")
    
    if not detail.get("object", {}).get("key"):
        raise ValidationError("Missing object key")
    
    # Validate file extension
    key = detail["object"]["key"]
    if not key.lower().endswith((".mp3", ".wav", ".m4a", ".ogg", ".flac")):
        raise ValidationError(f"Unsupported file format: {key}")
```

---

## Observability Patterns

### Structured Logging Pattern

```python
# Pattern for structured JSON logging
def log_structured(level: str, message: str, **kwargs) -> None:
    """Log structured JSON message."""
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "message": message,
        **kwargs
    }
    print(json.dumps(log_entry))

# Usage
log_structured("INFO", "Processing started", 
               audio_id=audio_id, 
               request_id=context.aws_request_id)
```

### X-Ray Tracing Pattern

```python
# Pattern for X-Ray tracing
lambda_function = lambda_.Function(self, "TracedFunction",
    runtime=lambda_.Runtime.PYTHON_3_12,
    handler="index.handler",
    code=lambda_.Code.from_asset("lambda"),
    tracing=lambda_.Tracing.ACTIVE  # Enable X-Ray tracing
)

state_machine = sfn.StateMachine(self, "TracedStateMachine",
    definition=definition,
    tracing_enabled=True  # Enable X-Ray tracing
)
```

### CloudWatch Alarms Pattern

```python
# Pattern for CloudWatch alarms
alarm = cloudwatch.Alarm(self, "CriticalFailureAlarm",
    metric=state_machine.metric_failed(
        period=Duration.minutes(5)
    ),
    threshold=1,
    evaluation_periods=1,
    comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD
)

alarm.add_alarm_action(actions.SnsAction(failure_topic))
```

### Retry Policy Pattern

```python
# Pattern for exponential backoff retries
lambda_task.add_retry(
    errors=["Lambda.ServiceException", "Lambda.AWSLambdaException"],
    interval=Duration.seconds(2),
    max_attempts=3,
    backoff_rate=2.0  # Exponential: 2s, 4s, 8s
)

dynamodb_task.add_retry(
    errors=["DynamoDB.ProvisionedThroughputExceededException"],
    interval=Duration.seconds(1),
    max_attempts=3,
    backoff_rate=2.0
)
```

---

## Best Practices

### Code Organization

1. **Separate Concerns**: Keep validation, processing, and I/O logic in separate functions
2. **Type Hints**: Use Python type hints for all function signatures
3. **Descriptive Names**: Use clear, descriptive names for all resources and variables
4. **DRY Principle**: Extract common patterns into helper functions or constructs

### Testing Strategy

1. **Fast Feedback**: Tests should run in seconds, not minutes
2. **Clear Names**: Test names should describe what they test and expected outcome
3. **Arrange-Act-Assert**: Follow AAA pattern for test structure
4. **One Assertion**: Each test should verify one specific behavior

### Documentation Standards

1. **User-Facing First**: README.md is for users, not developers
2. **Technical Details**: ARCHITECTURE.md contains all technical details
3. **Development Workflow**: AGENT_GUIDELINES.md contains development instructions
4. **Keep Synchronized**: Update docs in same PR as code changes

### Deployment Practices

1. **Dev First**: Always deploy to dev environment first
2. **Diff Before Deploy**: Review `cdk diff` output before deploying
3. **Monitor After Deploy**: Check CloudWatch Logs and alarms after deployment
4. **Rollback Plan**: Know how to rollback (redeploy previous version)

---

## Applying These Patterns

### For New Projects

1. **Setup Phase**:
   - Create ARCHITECTURE.md as single source of truth
   - Define validation commands in AGENT_GUIDELINES.md
   - Set up CI workflow with validation commands
   - Create initial test structure

2. **Development Phase**:
   - Follow strict TDD for all features
   - Enforce scope discipline per issue
   - Keep documentation synchronized
   - Run validation commands before each commit

3. **Maintenance Phase**:
   - Update patterns as you learn
   - Refine agent instructions based on outcomes
   - Document new patterns that emerge
   - Review and improve meta-prompts periodically

### For Existing Projects

1. **Audit Current State**:
   - Review documentation quality and coverage
   - Assess test coverage and quality
   - Identify architectural drift
   - Document technical debt

2. **Establish Patterns**:
   - Create or update ARCHITECTURE.md
   - Define validation commands
   - Set up CI if missing
   - Create agent guidelines

3. **Incremental Improvement**:
   - Apply patterns to new features first
   - Refactor existing code gradually
   - Update documentation iteratively
   - Improve test coverage over time

---

## Success Metrics

Track these metrics to evaluate pattern effectiveness:

1. **Code Quality**:
   - Test coverage percentage
   - Number of bugs in production
   - Time to fix bugs
   - Code review feedback volume

2. **Development Velocity**:
   - Time from issue creation to deployment
   - Number of PRs requiring rework
   - CI/CD success rate
   - Documentation completeness

3. **Agent Performance**:
   - Issues completed without human intervention
   - Number of scope violations
   - Test-first adherence rate
   - Documentation synchronization rate

4. **Maintenance**:
   - Time to onboard new contributors
   - Documentation staleness
   - Technical debt accumulation
   - Refactoring frequency

---

## References

- **Source Project**: [obstreperous-ai/cdk-sleep-py-copilot](https://github.com/obstreperous-ai/cdk-sleep-py-copilot)
- **ARCHITECTURE.md**: Complete system design and single source of truth
- **AGENT_GUIDELINES.md**: TDD workflow and contribution guidelines
- **SUMMARY.md**: Project journey, lessons learned, and recommendations

---

**Version**: 1.0  
**Last Updated**: 2026-06-12  
**Status**: Extracted from production-ready TDD IaC project with 138 passing tests
