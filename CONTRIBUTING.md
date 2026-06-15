# Contributing to Event-Driven Sleep Audio Pipeline

Thank you for your interest in contributing to the Event-Driven Sleep Audio Pipeline! This document provides guidelines for contributing to this project.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Pull Request Process](#pull-request-process)
- [Testing Guidelines](#testing-guidelines)
- [Documentation Guidelines](#documentation-guidelines)
- [Code Style](#code-style)
- [Questions and Support](#questions-and-support)

---

## Code of Conduct

This project follows the [GitHub Community Guidelines](https://docs.github.com/en/site-policy/github-terms/github-community-guidelines). By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

---

## Getting Started

### Prerequisites

- **AWS Account** with appropriate permissions
- **AWS CLI** configured with credentials
- **Python 3.12+** installed
- **Node.js 18+** and npm
- **AWS CDK CLI** v2.x (`npm install -g aws-cdk@2`)
- **Git** for version control

### Setting Up Your Development Environment

1. **Fork the repository** on GitHub

2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/cdk-sleep-py-copilot.git
   cd cdk-sleep-py-copilot
   ```

3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/obstreperous-ai/cdk-sleep-py-copilot.git
   ```

4. **Create Python virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate.bat
   ```

5. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

6. **Verify setup**:
   ```bash
   pytest -v
   cdk synth
   ```

---

## Development Workflow

This project follows **strict Test-Driven Development (TDD)**. Please follow this workflow for all contributions:

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

Use descriptive branch names:
- `feature/add-audio-mixing` for new features
- `fix/lambda-timeout-issue` for bug fixes
- `docs/update-readme` for documentation
- `test/improve-coverage` for test improvements

### 2. Follow TDD Workflow

**Write tests BEFORE implementation:**

```bash
# 1. Write a failing test
# Create or update test file in tests/unit/

# 2. Run test to confirm it fails
pytest tests/unit/test_your_feature.py -v

# 3. Implement minimal code to pass the test
# Edit files in cdk_base/ or lambda/

# 4. Run test to confirm it passes
pytest tests/unit/test_your_feature.py -v

# 5. Refactor while keeping tests green

# 6. Run all tests to ensure no regressions
pytest -v
```

### 3. Validate Your Changes

Before committing, run all validation commands:

```bash
# Run all tests
pytest -v

# Synthesize CloudFormation
cdk synth

# Verify diff
cdk diff --template cdk.out/CdkBaseStack.template.json
```

All commands must succeed before proceeding.

### 4. Update Documentation

If your changes affect:
- **System design** → Update `ARCHITECTURE.md`
- **User behavior** → Update `README.md`
- **Development process** → Update `AGENT_GUIDELINES.md`
- **Reusable patterns** → Update `META-PROMPTS.md`

Documentation updates **must be in the same PR** as code changes.

### 5. Commit Your Changes

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```bash
git add .
git commit -m "feat: add audio mixing capability"
# or
git commit -m "fix: resolve Lambda timeout issue"
# or
git commit -m "docs: update deployment instructions"
# or
git commit -m "test: add integration tests for audio processing"
```

**Commit message types**:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation only
- `test:` - Adding or updating tests
- `refactor:` - Code refactoring
- `chore:` - Maintenance tasks
- `perf:` - Performance improvements

### 6. Push to Your Fork

```bash
git push origin feature/your-feature-name
```

---

## Pull Request Process

### Before Opening a PR

Ensure you have:
- [ ] Followed TDD workflow (tests written first)
- [ ] All tests pass (`pytest -v`)
- [ ] CDK synth succeeds (`cdk synth`)
- [ ] Updated relevant documentation
- [ ] Followed code style guidelines
- [ ] Rebased on latest main branch
- [ ] Reviewed your own changes

### Opening a PR

1. **Create Pull Request** on GitHub from your fork to `obstreperous-ai/cdk-sleep-py-copilot:main`

2. **Use descriptive title**:
   - ✅ "feat: Add audio mixing with background sounds"
   - ✅ "fix: Resolve Lambda cold start timeout"
   - ❌ "Update code"
   - ❌ "Bug fix"

3. **Fill out PR description** with:
   - Summary of changes
   - Related issue number (if applicable): `Closes #123`
   - Testing performed
   - Screenshots/logs (if relevant)
   - Breaking changes (if any)

4. **Request review** from maintainers

### PR Review Process

- **Automated checks** (CI) must pass
- **Code review** by at least one maintainer
- **Address feedback** promptly
- **Keep PR updated** with main branch

### After PR Approval

- Maintainers will merge using **squash and merge**
- Your fork will not automatically update; sync it manually:
  ```bash
  git checkout main
  git pull upstream main
  git push origin main
  ```

---

## Testing Guidelines

### Test Organization

Tests are organized in `tests/unit/`:
- `test_cdk_base_stack.py` - Infrastructure tests
- `test_audio_processing.py` - Lambda function tests
- `test_lambda_validation.py` - Input validation tests
- `test_pipeline_integration.py` - Integration tests
- `test_error_handling_observability.py` - Error handling and observability
- `test_multi_environment.py` - Multi-environment configuration
- `test_end_to_end_validation.py` - End-to-end flow tests

### Writing Good Tests

```python
def test_descriptive_name_of_what_is_tested():
    """Test should have clear docstring."""
    # Arrange - Set up test data
    stack = CdkBaseStack(app, "TestStack", env_name="dev")
    template = Template.from_stack(stack)
    
    # Act - Perform the action (if needed)
    # (For infrastructure tests, this is often implicit)
    
    # Assert - Verify the outcome
    template.resource_count_is("AWS::S3::Bucket", 2)
    template.has_resource_properties("AWS::S3::Bucket", {
        "BucketEncryption": {
            "ServerSideEncryptionConfiguration": Match.any_value()
        }
    })
```

**Test Best Practices**:
- One test should verify one behavior
- Use descriptive test names
- Include docstrings explaining what is tested
- Use arrange-act-assert pattern
- Tests should be fast (all 143 tests run in ~52 seconds)
- Tests should be independent (no shared state)

### Running Tests

```bash
# Run all tests
pytest -v

# Run specific test file
pytest tests/unit/test_cdk_base_stack.py -v

# Run specific test class
pytest tests/unit/test_cdk_base_stack.py::TestClass -v

# Run specific test method
pytest tests/unit/test_cdk_base_stack.py::TestClass::test_method -v

# Run with coverage (if configured)
pytest --cov=cdk_base --cov=lambda -v
```

---

## Documentation Guidelines

### Documentation Structure

- **README.md** - User-facing documentation (deployment, usage, troubleshooting)
- **ARCHITECTURE.md** - Complete system design, single source of truth
- **AGENT_GUIDELINES.md** - TDD workflow and contribution process for agents
- **CONTRIBUTING.md** - This file (external contributor guidelines)
- **SUMMARY.md** - Project journey, key decisions, lessons learned
- **META-PROMPTS.md** - Reusable agent patterns and meta-prompts

### Writing Good Documentation

1. **Be Clear and Concise** - Use simple language, avoid jargon
2. **Include Examples** - Show code snippets and command examples
3. **Keep Updated** - Documentation must match current code
4. **Use Proper Markdown** - Follow Markdown best practices
5. **Add Table of Contents** - For documents longer than one screen

### Documentation Updates

- Update in **the same PR** as code changes
- Verify all internal links work
- Update version/date in document footer (if present)
- Follow existing documentation style

---

## Code Style

### Python Style

- Follow [PEP 8](https://pep8.org/) style guide
- Use **type hints** for all function signatures:
  ```python
  def process_audio(audio_id: str, bucket: str) -> Dict[str, Any]:
      """Process audio file and return metadata."""
      pass
  ```
- Write **docstrings** for all classes and functions:
  ```python
  def validate_input(event: Dict[str, Any]) -> None:
      """
      Validate Lambda event structure.
      
      Args:
          event: Lambda event dictionary
          
      Raises:
          ValidationError: If event structure is invalid
      """
      pass
  ```
- Use **descriptive variable names**:
  - ✅ `audio_id`, `input_bucket`, `processing_status`
  - ❌ `x`, `data`, `tmp`

### CDK Style

- Use **L2 constructs** when available (not L1 CfnResources)
- Use **descriptive construct IDs**:
  ```python
  input_bucket = s3.Bucket(self, "SleepAudioInputBucket")  # Good
  bucket = s3.Bucket(self, "Bucket1")  # Bad
  ```
- **Group related resources** together in code
- Add **comments** for complex configurations
- Follow **least-privilege IAM** principles

### Lambda Style

- Use **structured JSON logging**:
  ```python
  log_structured("INFO", "Processing started", 
                 audio_id=audio_id,
                 request_id=context.aws_request_id)
  ```
- Implement **input validation** in separate function
- Return **structured responses**:
  ```python
  return {
      "status": "success",
      "message": "Processing completed",
      "data": {
          "outputKey": output_key,
          "outputSize": output_size
      }
  }
  ```
- Handle **all exceptions** gracefully

---

## Questions and Support

### Getting Help

- **Issues**: Open an issue for bugs or feature requests
- **Discussions**: Use GitHub Discussions for questions
- **Documentation**: Check README.md and ARCHITECTURE.md first

### Reporting Bugs

When reporting bugs, include:
1. **Description** - Clear description of the issue
2. **Steps to Reproduce** - Exact steps to reproduce the bug
3. **Expected Behavior** - What you expected to happen
4. **Actual Behavior** - What actually happened
5. **Environment** - Python version, CDK version, OS
6. **Logs** - Relevant log output or error messages
7. **Screenshots** - If applicable

### Suggesting Features

When suggesting features:
1. **Use Case** - Describe the problem you're trying to solve
2. **Proposed Solution** - Your suggested approach
3. **Alternatives** - Other approaches you've considered
4. **Additional Context** - Any other relevant information

---

## Recognition

Contributors are recognized in several ways:
- Listed in GitHub contributors
- Mentioned in release notes (for significant contributions)
- Credit in SUMMARY.md for major features

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

## Additional Resources

- **AWS CDK Documentation**: https://docs.aws.amazon.com/cdk/
- **AWS Step Functions**: https://docs.aws.amazon.com/step-functions/
- **Amazon Polly**: https://docs.aws.amazon.com/polly/
- **pytest Documentation**: https://docs.pytest.org/
- **Conventional Commits**: https://www.conventionalcommits.org/

---

**Thank you for contributing to the Event-Driven Sleep Audio Pipeline!** 🎉
