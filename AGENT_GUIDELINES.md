# Agent & Contributor Guidelines

These guidelines apply to every contributor and automation agent working on the
**Event-Driven Sleep Audio Pipeline**.

## Source of Truth

[`ARCHITECTURE.md`](./ARCHITECTURE.md) is the **single source of truth** for the
system design. Before starting any issue:

1. Read `ARCHITECTURE.md` and ensure your change is consistent with the documented
   data flow, services, and Mermaid diagram.
2. If your change alters the design, **update `ARCHITECTURE.md` (description and
   diagram together) in the same pull request** so the document and the code never
   drift apart.

## Test-Driven Development (TDD)

All infrastructure changes follow a strict TDD workflow:

1. **Write a failing test first** under `tests/` using `aws_cdk.assertions`
   (`Template.from_stack(...)`) to assert the resources/properties you expect.
2. **Run the test and watch it fail** (`pytest`).
3. **Implement** the minimal CDK code in `cdk_base/` to make the test pass.
4. **Refactor** while keeping tests green.

## Validation Commands

Run these locally before opening a pull request (they mirror CI in
[`.github/workflows/ci.yml`](./.github/workflows/ci.yml)):

```bash
pytest
cdk synth
cdk diff --template cdk.out/CdkBaseStack.template.json
```

## Scope Discipline

- Keep changes **minimal and focused** on the current issue.
- Do not implement future-issue functionality ahead of time.
- Documentation-only issues (such as the initial architecture design) must not
  modify CDK stack code.

## Security & Best Practices

Follow the security baseline in `ARCHITECTURE.md`: private buckets, encryption at
rest and in transit, and least-privilege IAM roles. Never commit secrets.
