from typing import Any

from external_resources_io.input import AppInterfaceProvision
from pydantic import BaseModel


class CloudflareDNSRecord(BaseModel):
    """
    Data model for Cloudflare DNS Record

    https://registry.terraform.io/providers/cloudflare/cloudflare/latest/docs/resources/dns_record
    """

    identifier: str
    name: str
    ttl: int
    type: str
    content: str | None = None
    data: dict[str, Any] | None = None
    priority: int | None = None
    proxied: bool | None = None


class CloudflareRule(BaseModel):
    """
    Data model for Cloudflare Rule

    https://registry.terraform.io/providers/cloudflare/cloudflare/latest/docs/resources/ruleset#nestedatt--rules
    """

    action: str
    expression: str
    action_parameters: dict[str, Any] | None = None
    description: str | None = None
    enabled: bool | None = None
    ref: str | None = None


class CloudflareRuleset(BaseModel):
    """
    Data model for Cloudflare Ruleset

    https://registry.terraform.io/providers/cloudflare/cloudflare/latest/docs/resources/ruleset
    """

    identifier: str
    kind: str
    name: str
    phase: str
    description: str | None = None
    rules: list[CloudflareRule] = []


class CloudflareZone(BaseModel):
    """
    Data model for Cloudflare Zone

    https://registry.terraform.io/providers/cloudflare/cloudflare/latest/docs/resources/zone
    """

    account_id: str
    name: str
    plan: str | None = None
    type: str | None = None
    dns_records: list[CloudflareDNSRecord] = []
    rulesets: list[CloudflareRuleset] = []


class AppInterfaceInput(BaseModel):
    """Input model for AWS MSK"""

    data: CloudflareZone
    provision: AppInterfaceProvision
