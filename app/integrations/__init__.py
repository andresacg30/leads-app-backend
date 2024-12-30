from app.integrations.ringy import Ringy

CRM_REGISTRY = {
    "Ringy": Ringy
}


def crm_chooser(crm_name):
    try:
        return CRM_REGISTRY[crm_name]
    except KeyError:
        raise ValueError(f"Unknown CRM: {crm_name}")
