import aws_cdk as core
import aws_cdk.assertions as assertions
import pytest

from cdk_base.cdk_base_stack import CdkBaseStack


@pytest.fixture
def template() -> assertions.Template:
    app = core.App()
    stack = CdkBaseStack(app, "cdk-base")
    return assertions.Template.from_stack(stack)


def test_template_has_description(template: assertions.Template):
    template.template_matches(
        assertions.Match.object_like(
            {"Description": "Event-driven sleep audio pipeline base infrastructure"}
        )
    )
