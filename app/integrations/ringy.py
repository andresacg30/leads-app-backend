import requests
from typing import Optional, Dict, Any

class Ringy:
    """
    Integration class for Ringy CRM.

    Attributes:
        auth_token (str): Authorization token to authenticate with Ringy.
        sid (str): Session ID or unique identifier for the account.
    """

    BASE_URL = "https://api.ringy.com"  # Example URL; adjust as needed.

    def __init__(self, auth_token: str, sid: str) -> None:
        """
        Initialize the Ringy integration with authentication details.

        Args:
            auth_token (str): The Ringy auth token.
            sid (str): The Ringy session ID or account ID.
        """
        self.auth_token = auth_token
        self.sid = sid

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
        try:
            response = requests.post(
                f"{self.BASE_URL}/leads/new-lead",
                headers=self._get_headers(),
                json=lead_data,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
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
