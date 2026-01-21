"""Import existing Cloudflare resources into Terraform state."""

import logging
import subprocess

from cloudflare import Cloudflare
from external_resources_io.config import Config
from external_resources_io.input import parse_model, read_input_from_file
from external_resources_io.log import setup_logging
from external_resources_io.terraform import terraform_run
from pydantic import BaseModel

from .app_interface_input import (
    AppInterfaceInput,
    CloudflareDNSRecord,
    CloudflareRuleset,
    CloudflareZone,
)

logger = logging.getLogger(__name__)


class ZoneNotFoundError(Exception):
    """Raised when a zone cannot be found in Cloudflare."""


class ImportResult(BaseModel):
    """Result of a terraform import operation."""

    resource_address: str
    import_id: str
    success: bool
    error_message: str | None = None


def get_ai_input() -> AppInterfaceInput:
    """Get the AppInterfaceInput from the input file."""
    return parse_model(AppInterfaceInput, read_input_from_file())


def lookup_zone_id(client: Cloudflare, zone_name: str) -> str | None:
    """Look up the zone ID by zone name.

    Args:
        client: Cloudflare API client.
        zone_name: The domain name (e.g., "openshift.io").

    Returns:
        The zone ID if found, None otherwise.
    """
    zones = client.zones.list(name=zone_name)
    for zone in zones:
        if zone.name == zone_name:
            return zone.id
    return None


def import_resource(
    resource_address: str,
    import_id: str,
    *,
    dry_run: bool = False,
) -> ImportResult:
    """Execute terraform import for a single resource.

    Args:
        resource_address: Terraform resource address (e.g., "cloudflare_zone.this").
        import_id: The import ID (e.g., "zone_id" or "zone_id/record_id").
        dry_run: If True, only log the command without executing.

    Returns:
        ImportResult with success status and any error message.
    """
    try:
        terraform_run(["import", resource_address, import_id], dry_run=dry_run)
        logger.info("Successfully imported %s", resource_address)
        return ImportResult(
            resource_address=resource_address,
            import_id=import_id,
            success=True,
        )
    except subprocess.CalledProcessError as e:
        error_msg = str(e.stderr) if e.stderr else str(e)
        logger.warning("Failed to import %s: %s", resource_address, error_msg)
        return ImportResult(
            resource_address=resource_address,
            import_id=import_id,
            success=False,
            error_message=error_msg,
        )


def import_zone(zone_id: str, *, dry_run: bool = False) -> ImportResult:
    """Import the zone."""
    return import_resource("cloudflare_zone.this", zone_id, dry_run=dry_run)


def import_zone_subscription(zone_id: str, *, dry_run: bool = False) -> ImportResult:
    """Import zone subscription."""
    return import_resource(
        "cloudflare_zone_subscription.this[0]", zone_id, dry_run=dry_run
    )


def import_dns_records(
    client: Cloudflare,
    zone_id: str,
    records: list[CloudflareDNSRecord],
    *,
    dry_run: bool = False,
) -> list[ImportResult]:
    """Import DNS records."""
    try:
        dns_record_by_key = {
            (record.name, str(record.type), record.content): record.id
            for record in client.dns.records.list(zone_id=zone_id)
        }
    except Exception:
        logger.exception("Failed to list DNS records for zone ID %s", zone_id)
        return []
    results: list[ImportResult] = []
    for record in records:
        record_id = dns_record_by_key.get((record.name, record.type, record.content))
        resource_address = f'cloudflare_dns_record.this["{record.identifier}"]'
        if record_id is None:
            error_msg = f"DNS record '{record.name}' ({record.type}) not found"
            logger.error(error_msg)
            results.append(
                ImportResult(
                    resource_address=resource_address,
                    import_id="",
                    success=False,
                    error_message=error_msg,
                )
            )
        else:
            results.append(
                import_resource(
                    resource_address,
                    f"{zone_id}/{record_id}",
                    dry_run=dry_run,
                )
            )
    return results


def import_rulesets(
    client: Cloudflare,
    zone_id: str,
    rulesets: list[CloudflareRuleset],
    *,
    dry_run: bool = False,
) -> list[ImportResult]:
    """Import rulesets."""
    try:
        ruleset_by_key = {
            (ruleset.name, str(ruleset.phase)): ruleset.id
            for ruleset in client.rulesets.list(zone_id=zone_id)
        }
    except Exception:
        logger.exception("Failed to list rulesets for zone ID %s", zone_id)
        return []
    results: list[ImportResult] = []
    for ruleset in rulesets:
        ruleset_id = ruleset_by_key.get((ruleset.name, ruleset.phase))
        resource_address = f'cloudflare_ruleset.this["{ruleset.identifier}"]'
        if ruleset_id is None:
            error_msg = f"Ruleset '{ruleset.name}' (phase: {ruleset.phase}) not found"
            logger.error(error_msg)
            results.append(
                ImportResult(
                    resource_address=resource_address,
                    import_id="",
                    success=False,
                    error_message=error_msg,
                )
            )
        else:
            results.append(
                import_resource(
                    resource_address,
                    f"zones/{zone_id}/{ruleset_id}",
                    dry_run=dry_run,
                )
            )
    return results


def import_state(
    client: Cloudflare,
    zone: CloudflareZone,
    *,
    dry_run: bool = False,
) -> list[ImportResult]:
    """Import all resources for a Cloudflare zone.

    Args:
        client: Cloudflare API client.
        zone: The CloudflareZone configuration.
        dry_run: If True, only log commands without executing.

    Returns:
        List of ImportResult for each import operation.
    """
    logger.info("Looking up zone ID for '%s'", zone.name)
    zone_id = lookup_zone_id(client, zone.name)

    if zone_id is None:
        msg = f"Zone '{zone.name}' not found in Cloudflare"
        logger.error(msg)
        raise ZoneNotFoundError(msg)

    logger.info("Found zone ID: %s", zone_id)

    return (
        [import_zone(zone_id, dry_run=dry_run)]
        + (
            [import_zone_subscription(zone_id, dry_run=dry_run)]
            if zone.plan is not None
            else []
        )
        + import_dns_records(client, zone_id, zone.dns_records, dry_run=dry_run)
        + import_rulesets(client, zone_id, zone.rulesets, dry_run=dry_run)
    )


def main() -> None:
    """Main entry point for import-tfstate CLI."""
    setup_logging()
    config = Config()

    ai_input = get_ai_input()
    client = Cloudflare()

    results = import_state(client, ai_input.data, dry_run=config.dry_run)

    succeeded = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)

    logger.info("Import complete: %d succeeded, %d failed", succeeded, failed)

    if failed > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
