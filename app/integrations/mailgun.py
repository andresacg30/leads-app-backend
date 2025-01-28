import requests
import logging

from app.background_jobs.job import enqueue_background_job
from app.tools.constants import FROM_EMAIL_ADDRESS
from settings import get_settings

settings = get_settings()

logging.basicConfig(level=logging.INFO)

MAILGUN_API_URL = "https://api.mailgun.net/v3/mg.leadconex.org/messages"


def mailgun_email(to_address: str, subject: str, template: str, text: str):
    try:
        response = requests.post(
            MAILGUN_API_URL,
            auth=("api", settings.mailgun_api_key),
            data={
                "from": FROM_EMAIL_ADDRESS,
                "to": to_address,
                "subject": subject,
                "html": template,
                "text": text
            }
        )
        response.raise_for_status()
        logging.info(f"Email sent to {to_address}")
    except Exception as e:
        logging.error(f"Error sending email: {e}")
        raise e


def send_single_email(to_address: str, subject: str, template: str, text: str):
    enqueue_background_job(
        'app.integrations.mailgun.mailgun_email',
        to_address,
        subject,
        template,
        text
    )


def send_batch_email(to_addresses: list, subject: str, template: str, text: str):
    addresses = {address: {"unique_id": "%recipient.unique_id%"} for address in to_addresses}
    send_single_email(
        to_address=addresses,
        subject=subject,
        template=template,
        text=text
    )
