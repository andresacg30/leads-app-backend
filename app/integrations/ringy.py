import logging
import requests
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class Ringy:
    """
    Integration class for Ringy CRM.

    Attributes:
        auth_token (str): Authorization token to authenticate with Ringy.
        sid (str): Session ID or unique identifier for the account.
    """

    BASE_URL = "https://app.ringy.com/api/public"

    def __init__(self, integration_details: dict) -> None:
        """
        Initialize the Ringy integration with authentication details.

        Args:
            auth_token (str): The Ringy auth token.
            sid (str): The Ringy session ID or account ID.
        """
        self.auth_token = integration_details.get("auth_token")
        self.sid = integration_details.get("sid")

    def __str__(self) -> str:
        """
        Return a string representation (for debugging).

        Returns:
            str: A summary of the instance, including auth_token and sid.
        """
        return f"Ringy(auth_token={self.auth_token}, sid={self.sid})"

    def push_lead(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Push/insert new lead data to Ringy.

        Args:
            lead_data (dict): The lead information you want to create or update in Ringy.

        Returns:
            dict: The API response, possibly containing the new lead ID or an error.
        """
        custom_fields = lead_data.pop('custom_fields', {}) or {}
        normalized_custom_fields = {}
        for key, value in custom_fields.items():
            normalized_key = self._normalize_field_name(key)
            normalized_custom_fields[normalized_key] = value
        lead_data.update(normalized_custom_fields)
        lead_data.update({
            "sid": self.sid,
            "authToken": self.auth_token
        })
        try:
            response = requests.post(
                f"{self.BASE_URL}/leads/new-lead",
                headers=self._get_headers(),
                json=lead_data,
                timeout=10
            )
            response.raise_for_status()
            logger.info(f"Ringy response: {response.json()}")
            return response.json()
        except requests.RequestException as exc:
            logger.error(f"Error pushing lead to Ringy: {exc}")
            return {"error": str(exc)}

    def _get_headers(self) -> Dict[str, str]:
        """
        Return the default headers for Ringy requests.

        Returns:
            dict: A dictionary with 'Authorization' and potentially other headers.
        """
        return {
            "Content-Type": "application/json"
        }

    def _normalize_field_name(self, field_name: str) -> str:
        """
        Normalize field names to lowercase with underscores.

        Args:
            field_name (str): The original field name (e.g., "Current Coverage")

        Returns:
            str: The normalized field name (e.g., "current_coverage")
        """
        return field_name.replace(' ', '_').lower()
