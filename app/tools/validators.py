import datetime

from app.models.lead import LeadModel
from app.models.campaign import CampaignModel


def validate_phone_number(phone_number):
    if len(phone_number) != 10:
        return False
    return True


async def validate_duplicate(lead: LeadModel, campaign_id: str):
    from app.controllers.lead import get_lead_by_field, LeadNotFoundError
    from app.controllers.campaign import get_one_campaign

    campaign: CampaignModel = await get_one_campaign(campaign_id)
    try:
        existing_lead: dict = await get_lead_by_field(phone=lead.phone, campaign_id=campaign_id)
        existing_lead = LeadModel(**existing_lead)
        if existing_lead:
            duplication_max_date = datetime.datetime.utcnow() - datetime.timedelta(days=campaign.duplicate_cutoff_days)
            if existing_lead.created_time >= duplication_max_date:
                return True
            return False
    except LeadNotFoundError:
        return False
    return False
