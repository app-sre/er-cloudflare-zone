import pytest
from external_resources_io.input import parse_model

from er_cloudflare_zone.app_interface_input import AppInterfaceInput


@pytest.fixture
def raw_input_data() -> dict:
    """Fixture to provide test data for the AppInterfaceInput."""
    return {
        "data": {
            "name": "example.com",
            "type": "full",
            "plan": "enterprise",
            "account_id": "some-id",
            "records": [
                {
                    "identifier": "a-example-com",
                    "name": "example.com",
                    "type": "A",
                    "ttl": 86400,
                    "content": "192.0.2.0",
                    "proxied": False,
                },
                {
                    "identifier": "a-www-example-com",
                    "name": "www.example.com",
                    "type": "A",
                    "ttl": 1,
                    "value": "192.0.2.0",
                    "proxied": True,
                },
            ],
            "rulesets": [
                {
                    "identifier": "redirects",
                    "name": "redirects",
                    "kind": "zone",
                    "phase": "http_request_dynamic_redirect",
                    "description": "Redirects",
                    "rules": [
                        {
                            "ref": "redirect-www-to-root",
                            "expression": '(http.request.full_uri wildcard "http*://www.example.com/*")',
                            "action": "redirect",
                            "description": "redirect www to root",
                            "enabled": True,
                            "action_parameters": {
                                "from_value": {
                                    "target_url": {
                                        "value": "https://example.com/",
                                    },
                                    "status_code": 301,
                                    "preserve_query_string": True,
                                }
                            },
                        }
                    ],
                }
            ],
        },
        "provision": {
            "provision_provider": "cloudflare",
            "provisioner": "dev",
            "provider": "zone",
            "identifier": "cloudflare-zone-example",
            "target_cluster": "appint-ex-01",
            "target_namespace": "cloudflare-zone-example",
            "target_secret_name": "creds-cloudflare-zone-example",
            "module_provision_data": {
                "tf_state_bucket": "external-resources-terraform-state-dev",
                "tf_state_region": "us-east-1",
                "tf_state_dynamodb_table": "external-resources-terraform-lock",
                "tf_state_key": "cloudflare/dev/zone/cloudflare-zone-example/terraform.tfstate",
            },
        },
    }


@pytest.fixture
def ai_input(raw_input_data: dict) -> AppInterfaceInput:
    """Fixture to provide the AppInterfaceInput."""
    return parse_model(AppInterfaceInput, raw_input_data)
