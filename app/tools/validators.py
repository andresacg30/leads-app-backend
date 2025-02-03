import datetime

from app.models.lead import LeadModel
from app.models.campaign import CampaignModel


def validate_phone_number(phone_number):
    digits_only = ''.join(filter(str.isdigit, phone_number))

    if len(digits_only) == 11 and digits_only.startswith('1'):
        digits_only = digits_only[1:]

    return len(digits_only) == 10


async def validate_duplicate(lead: LeadModel, campaign_id: str):
    from app.controllers.lead import get_lead_by_field, LeadNotFoundError
    from app.controllers.campaign import get_one_campaign

    campaign: CampaignModel = await get_one_campaign(campaign_id)
    try:
        existing_lead: dict = await get_lead_by_field(phone=lead.phone, campaign_id=campaign_id)
        existing_lead = LeadModel(**existing_lead)
        if existing_lead:
            duplication_max_date = datetime.datetime.utcnow() - datetime.timedelta(days=campaign.duplication_cutoff_days)
            if existing_lead.created_time >= duplication_max_date:
                return True
            return False
    except LeadNotFoundError:
        return False
    return False
