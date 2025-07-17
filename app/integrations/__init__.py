import logging

from app.integrations.ringy import Ringy
from app.integrations.gohighlevel import GoHighLevel


logger = logging.getLogger(__name__)


CRM_REGISTRY = {
    "Ringy": Ringy
}


def get_crm(crm_name: str):
    """
    Factory function to choose the appropriate CRM integration class based on the CRM name.
    """
    logger.debug(f"Choosing CRM integration for: {crm_name}")
    if crm_name == "Ringy":
        return Ringy
    if crm_name == "GoHighLevel":
        return GoHighLevel
    raise NotImplementedError(f"CRM {crm_name} is not implemented yet.")
