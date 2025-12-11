from external_resources_io.input import AppInterfaceProvision
from pydantic import BaseModel


class CloudflareZoneData(BaseModel):
    """Data model for Cloudflare Zone"""


class AppInterfaceInput(BaseModel):
    """Input model for AWS MSK"""

    data: CloudflareZoneData
    provision: AppInterfaceProvision
