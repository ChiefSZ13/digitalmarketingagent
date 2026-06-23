from openapi_spec_validator import validate

from marketing_agent.main import create_app


def test_openapi_schema_is_valid() -> None:
    schema = create_app().openapi()
    validate(schema)
    assert schema["openapi"].startswith("3.1")
