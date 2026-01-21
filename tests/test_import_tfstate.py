"""Tests for import_tfstate module."""

import subprocess
from collections.abc import Iterator
from unittest.mock import MagicMock, call, create_autospec, patch

import pytest
from cloudflare.types.dns.record_response import ARecord
from cloudflare.types.rulesets import RulesetListResponse
from cloudflare.types.zones import Zone

from er_cloudflare_zone.import_tfstate import ZoneNotFoundError, main


def setup_cloudflare_client(
    mock_cloudflare: MagicMock,
    mock_zone: Zone,
    *,
    dns_records: list | None = None,
    rulesets: list | None = None,
) -> MagicMock:
    """Configure the Cloudflare client mock with zone, DNS records, and rulesets."""
    mock_client = mock_cloudflare.return_value
    mock_client.zones.list.return_value = [mock_zone]
    mock_client.dns.records.list.return_value = dns_records or []
    mock_client.rulesets.list.return_value = rulesets or []
    return mock_client


def build_input_data(
    *,
    plan: str | None = None,
    dns_records: list[dict] | None = None,
    rulesets: list[dict] | None = None,
) -> dict:
    """Build input data with optional overrides."""
    return {
        "data": {
            "name": "example.com",
            "account_id": "acct-123",
            "plan": plan,
            "dns_records": dns_records or [],
            "rulesets": rulesets or [],
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
                "tf_state_key": "cloudflare/dev/zone/example/terraform.tfstate",
            },
        },
    }


@pytest.fixture
def mock_zone() -> Zone:
    """Create a mock zone."""
    mock = create_autospec(Zone, instance=True)
    mock.configure_mock(id="zone-123", name="example.com")
    return mock


@pytest.fixture
def mock_read_input() -> Iterator[MagicMock]:
    """Mock read_input_from_file."""
    with patch("er_cloudflare_zone.import_tfstate.read_input_from_file") as mock:
        yield mock


@pytest.fixture
def mock_cloudflare() -> Iterator[MagicMock]:
    """Mock Cloudflare client."""
    with patch("er_cloudflare_zone.import_tfstate.Cloudflare") as mock:
        yield mock


@pytest.fixture
def mock_terraform_run() -> Iterator[MagicMock]:
    """Mock terraform_run."""
    with patch("er_cloudflare_zone.import_tfstate.terraform_run") as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_logger() -> Iterator[MagicMock]:
    """Mock logger to suppress log output in tests."""
    with patch("er_cloudflare_zone.import_tfstate.logger") as mock:
        yield mock


@pytest.fixture
def mock_dry_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DRY_RUN", "True")


@pytest.fixture
def mock_non_dry_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DRY_RUN", "False")


def test_import_zone_only(
    mock_non_dry_run: None,  # noqa: ARG001
    mock_terraform_run: MagicMock,
    mock_cloudflare: MagicMock,
    mock_read_input: MagicMock,
    mock_zone: Zone,
) -> None:
    """Test importing zone without DNS records or rulesets."""
    mock_read_input.return_value = build_input_data()
    setup_cloudflare_client(mock_cloudflare, mock_zone)

    main()

    assert mock_terraform_run.call_count == 1
    mock_terraform_run.assert_called_with(
        ["import", "cloudflare_zone.this", "zone-123"],
        dry_run=False,
    )


def test_import_zone_with_plan(
    mock_non_dry_run: None,  # noqa: ARG001
    mock_terraform_run: MagicMock,
    mock_cloudflare: MagicMock,
    mock_read_input: MagicMock,
    mock_zone: Zone,
) -> None:
    """Test importing zone with plan subscription."""
    mock_read_input.return_value = build_input_data(plan="enterprise")
    setup_cloudflare_client(mock_cloudflare, mock_zone)

    main()

    mock_terraform_run.assert_has_calls([
        call(["import", "cloudflare_zone.this", "zone-123"], dry_run=False),
        call(
            ["import", "cloudflare_zone_subscription.this[0]", "zone-123"],
            dry_run=False,
        ),
    ])


def test_import_zone_with_dns_records(
    mock_non_dry_run: None,  # noqa: ARG001
    mock_terraform_run: MagicMock,
    mock_cloudflare: MagicMock,
    mock_read_input: MagicMock,
    mock_zone: Zone,
) -> None:
    """Test importing zone with DNS records."""
    mock_read_input.return_value = build_input_data(
        dns_records=[
            {
                "identifier": "www-a-record",
                "name": "www.example.com",
                "type": "A",
                "ttl": 300,
                "content": "192.0.2.1",
            }
        ]
    )

    mock_record = create_autospec(ARecord, instance=True)
    mock_record.configure_mock(
        id="record-456",
        name="www.example.com",
        type="A",
        content="192.0.2.1",
    )
    setup_cloudflare_client(mock_cloudflare, mock_zone, dns_records=[mock_record])

    main()

    mock_terraform_run.assert_has_calls([
        call(["import", "cloudflare_zone.this", "zone-123"], dry_run=False),
        call(
            [
                "import",
                'cloudflare_dns_record.this["www-a-record"]',
                "zone-123/record-456",
            ],
            dry_run=False,
        ),
    ])


def test_import_zone_with_rulesets(
    mock_non_dry_run: None,  # noqa: ARG001
    mock_terraform_run: MagicMock,
    mock_cloudflare: MagicMock,
    mock_read_input: MagicMock,
    mock_zone: Zone,
) -> None:
    """Test importing zone with rulesets."""
    mock_read_input.return_value = build_input_data(
        rulesets=[
            {
                "identifier": "redirect-ruleset",
                "name": "redirects",
                "kind": "zone",
                "phase": "http_request_dynamic_redirect",
            }
        ]
    )

    mock_ruleset = create_autospec(RulesetListResponse, instance=True)
    mock_ruleset.configure_mock(
        id="ruleset-789", name="redirects", phase="http_request_dynamic_redirect"
    )
    setup_cloudflare_client(mock_cloudflare, mock_zone, rulesets=[mock_ruleset])

    main()

    mock_terraform_run.assert_has_calls([
        call(["import", "cloudflare_zone.this", "zone-123"], dry_run=False),
        call(
            [
                "import",
                'cloudflare_ruleset.this["redirect-ruleset"]',
                "zones/zone-123/ruleset-789",
            ],
            dry_run=False,
        ),
    ])


def test_zone_not_found(
    mock_non_dry_run: None,  # noqa: ARG001
    mock_cloudflare: MagicMock,
    mock_read_input: MagicMock,
) -> None:
    """Test ZoneNotFoundError when zone doesn't exist in Cloudflare."""
    mock_read_input.return_value = build_input_data()
    mock_client = mock_cloudflare.return_value
    mock_client.zones.list.return_value = []

    with pytest.raises(ZoneNotFoundError, match=r"example\.com"):
        main()


def test_dns_record_not_found_fails(
    mock_non_dry_run: None,  # noqa: ARG001
    mock_terraform_run: MagicMock,
    mock_cloudflare: MagicMock,
    mock_read_input: MagicMock,
    mock_zone: Zone,
) -> None:
    """Test DNS record not in Cloudflare causes failure."""
    mock_read_input.return_value = build_input_data(
        dns_records=[
            {
                "identifier": "missing-record",
                "name": "missing.example.com",
                "type": "A",
                "ttl": 300,
                "content": "192.0.2.1",
            }
        ]
    )
    setup_cloudflare_client(mock_cloudflare, mock_zone)

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    assert mock_terraform_run.call_count == 1


def test_ruleset_not_found_fails(
    mock_non_dry_run: None,  # noqa: ARG001
    mock_terraform_run: MagicMock,
    mock_cloudflare: MagicMock,
    mock_read_input: MagicMock,
    mock_zone: Zone,
) -> None:
    """Test ruleset not in Cloudflare causes failure."""
    mock_read_input.return_value = build_input_data(
        rulesets=[
            {
                "identifier": "missing-ruleset",
                "name": "missing",
                "kind": "zone",
                "phase": "http_request_dynamic_redirect",
            }
        ]
    )
    setup_cloudflare_client(mock_cloudflare, mock_zone)

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    assert mock_terraform_run.call_count == 1


def test_import_failure_exits_with_error(
    mock_non_dry_run: None,  # noqa: ARG001
    mock_terraform_run: MagicMock,
    mock_cloudflare: MagicMock,
    mock_read_input: MagicMock,
    mock_zone: Zone,
) -> None:
    """Test main exits with code 1 when terraform import fails."""
    mock_read_input.return_value = build_input_data()
    setup_cloudflare_client(mock_cloudflare, mock_zone)
    mock_terraform_run.side_effect = subprocess.CalledProcessError(
        returncode=1, cmd=["terraform", "import"]
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1


def test_dry_run_flag(
    mock_dry_run: None,  # noqa: ARG001
    mock_terraform_run: MagicMock,
    mock_cloudflare: MagicMock,
    mock_read_input: MagicMock,
    mock_zone: Zone,
) -> None:
    """Test dry_run config is passed to terraform_run."""
    mock_read_input.return_value = build_input_data()
    setup_cloudflare_client(mock_cloudflare, mock_zone)

    main()

    mock_terraform_run.assert_called_with(
        ["import", "cloudflare_zone.this", "zone-123"],
        dry_run=True,
    )
