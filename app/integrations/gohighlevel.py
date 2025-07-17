import httpx
import logging
from app.models.lead import LeadModel

logger = logging.getLogger(__name__)

class GoHighLevel:
    """
    Handles sending leads to the GoHighLevel API.
    """
    BASE_URL = "https://rest.gohighlevel.com/v1/contacts/"


    @staticmethod
    async def send_lead(lead: LeadModel, api_key: str, campaign_name: str):
        """
        Sends a lead to the GoHighLevel API to create a new contact.

        Args:
            lead (LeadModel): The lead object containing all lead data.
            api_key (str): The GoHighLevel API key for the agent's location.
            campaign (CampaignModel): The campaign object containing the custom field mapping.
        """
        if not api_key:
            logger.warning(f"GoHighLevel API key is missing for lead {lead.id}. Cannot send.")
            return None

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Version": "2021-07-28",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        lead_type = "second_chance" if lead.is_second_chance else "fresh"

        # 1. Standard Data Payload
        payload = {
            "firstName": lead.first_name,
            "lastName": lead.last_name,
            "email": lead.email,
            "phone": lead.phone,
            "state": lead.state,
            # 2. Tagging Logic
            "tags": [lead_type, "LeadConex", campaign_name],
            "customField": lead.custom_fields or {}
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url=GoHighLevel.BASE_URL, headers=headers, json=payload)
                if response.status_code in [200, 201]:
                    logger.info(f"Successfully sent lead {lead.id} to GoHighLevel.")
                    return response.json()
                else:
                    logger.error(
                        f"Failed to send lead {lead.id} to GHL. Status: {response.status_code}, Response: {response.text}. "
                        "This is most likely due to an invalid or incorrect API Key for this location."
                    )
                    return None
        except Exception as e:
            logger.error(f"An exception occurred while sending lead {lead.id} to GoHighLevel: {e}")
            return None
