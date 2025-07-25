import datetime
import math
from bson import ObjectId
from pydantic import BaseModel, Field, EmailStr, ConfigDict, computed_field, root_validator
from pydantic import validator, field_validator
from typing import List, Optional, Dict, Union, Literal, Annotated

from app.models.user import BalanceModel
from app.tools.modifiers import PyObjectId


class IntegrationDetail(BaseModel):
    auth_token: str
    sid: str
    type: str

    def to_json(self):
        return {
            "auth_token": self.auth_token,
            "sid": self.sid,
            "type": self.type
        }
    

class RingyFreshIntegration(BaseModel):
    auth_token: Optional[str] = None
    sid: Optional[str] = None
    type: Literal['fresh']

class RingySecondChanceIntegration(BaseModel):
    auth_token: Optional[str] = None
    sid: Optional[str] = None
    type: Literal['second_chance']

class GoHighLevelIntegration(BaseModel):
    api_key: Optional[str] = None
    type: Literal['gohighlevel']


AnyIntegrationDetail = Union[RingyFreshIntegration, RingySecondChanceIntegration, GoHighLevelIntegration]

DiscriminatedIntegrationDetail = Annotated[AnyIntegrationDetail, Field(discriminator="type")]


class IntegrationDetailsUpdate(BaseModel):
    integration_details: List[DiscriminatedIntegrationDetail]
    crm_name: str

    def to_json(self):
        return {
            "integration_details": [detail.to_json() for detail in self.integration_details]
        }


class CRMModel(BaseModel):
    """
    Container for a single CRM record.
    """
    name: Optional[str] = Field(default=None)
    url: Optional[str] = Field(default=None)
    integration_details: Optional[Dict[str, List[DiscriminatedIntegrationDetail]]] = Field(default_factory=dict)

    @root_validator(pre=True)
    def handle_integration_details(cls, values):
        def clean_nan_values(obj):
            if isinstance(obj, dict):
                return {k: clean_nan_values(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_nan_values(v) for v in obj]
            elif isinstance(obj, float) and math.isnan(obj):
                return None
            return obj

        integration_details = values.get('integration_details')

        # If details are missing or not a dictionary, reset to empty to prevent errors
        if not isinstance(integration_details, dict):
            values['integration_details'] = {}
            return values

        integration_details = clean_nan_values(integration_details)
        
        # Check for and discard old flat structures that are no longer supported
        flat_legacy_keys = {'SID', 'Auth Token', 'API Key', 'Google Sheet ID', 'username'}
        if set(integration_details.keys()) & flat_legacy_keys:
            values['integration_details'] = {}
            return values

        # Process the expected campaign-nested structure
        new_campaign_details = {}
        for campaign_id, details in integration_details.items():
            
            # The value for a campaign MUST be a list. If not, skip it.
            # This handles the 'list_type' error for "Google Sheet ID", "username", etc.
            if not isinstance(details, list):
                continue

            # It's a list. Now, clean the items inside it.
            cleaned_list = []
            for item in details:
                # Each item must be a dict with a valid 'type' to be kept.
                # This handles the 'union_tag_invalid' error.
                if isinstance(item, dict) and item.get('type') in ('fresh', 'second_chance', 'gohighlevel'):
                    cleaned_list.append(item)

            if cleaned_list:
                new_campaign_details[campaign_id] = cleaned_list
        
        values['integration_details'] = new_campaign_details
        return values


    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "name": "Ringy",
                "url": "www.ringy.com",
                "integration_details": {
                    "5f9c0a9e9c6d4b1e9c6d4b1e": [
                        {
                            "auth_token": "value1",
                            "sid": "value2",
                            "type": "fresh"
                        },
                        {
                            "auth_token": "value3",
                            "sid": "value4",
                            "type": "second_chance"
                        }
                    ],
                    "5f9c0a9e9c6d4b1e9c6d4b1f": [
                        {
                            "auth_token": "value5",
                            "sid": "value6",
                            "type": "fresh"
                        },
                        {
                            "auth_token": "value7",
                            "sid": "value8",
                            "type": "second_chance"
                        }
                    ]
                }
            }
        }
    )

    def get_campaign_integration_details(self, campaign_id: str) -> List[AnyIntegrationDetail]:
        """
        Retrieve the integration details for a specific campaign.

        Args:
            campaign_id (str): The ID of the campaign to retrieve details for.

        Returns:
            dict: The integration details for the specified campaign.
        """
        return self.integration_details.get(campaign_id, {})

    def update_integration_details(self, campaign_id: str, details: List[AnyIntegrationDetail]) -> None:
        """
        Update the integration details for a specific campaign.

        Args:
            campaign_id (str): The ID of the campaign to update details for.
            details (dict): The new integration details for the specified campaign.
        """
        self.integration_details[campaign_id] = details


class CRMCollection(BaseModel):
    """
    A container holding a list of `CRMModel` instances.

    This exists because providing a top-level array in a JSON response can be a [vulnerability](https://haacked.com/archive/2009/06/25/json-hijacking.aspx/)
    """
    CRMs: List[CRMModel]


class AgentCredentials(BaseModel):
    """
    A container holding the data needed to deliver a lead to a Agent.
    """
    username: Optional[str] = Field(default=None)
    password: Optional[str] = Field(default=None)


class DailyLeadLimit(BaseModel):
    campaign_id: Optional[PyObjectId] = Field(alias="campaign_id", default=None)
    limit: Optional[int] = Field(default=10)


class AgentModel(BaseModel):
    """
    Container for a single Agent record.
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    first_name: str = Field(...)
    last_name: str = Field(...)
    email: EmailStr = Field(...)
    phone: str = Field(...)
    states_with_license: List = Field(...)
    CRM: CRMModel = Field(default_factory=CRMModel)
    balance: Union[List[BalanceModel], float, None] = Field(default_factory=list)
    balance_total: Optional[float] = Field(default=None)
    lead_price_override: Optional[Union[float, Dict]] = Field(default=None)
    second_chance_lead_price_override: Optional[Union[float, Dict]] = Field(default=None)
    distribution_type: Optional[str] = Field(default="mixed")
    created_time: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    campaigns: List[PyObjectId] = Field(default_factory=list)
    credentials: AgentCredentials = Field(default_factory=AgentCredentials)
    daily_lead_limit: Optional[List[DailyLeadLimit]] = Field(default_factory=list)
    custom_campaign_responses: dict = Field(default_factory=dict)
    custom_fields: Optional[dict] = Field(default=None)

    @validator('phone', pre=True, always=True)
    def ensure_phone_is_str(cls, v):
        if isinstance(v, int):
            return str(v)
        return v

    @field_validator('campaigns', mode='before')
    def validate_campaigns(cls, v):
        if isinstance(v, list):
            return [PyObjectId(i) if not isinstance(i, ObjectId) else i for i in v]
        raise ValueError('Invalid campaigns list')

    @root_validator(pre=True)
    def strip_fields(cls, values):
        fields_to_strip = ['first_name', 'last_name', 'phone', 'email']
        for field in fields_to_strip:
            if field in values and isinstance(values[field], str):
                values[field] = values[field].strip()
        return values

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "janedoe@example.com",
                "phone": "555-555-5555",
                "states_with_license": ["CA", "NY"],
                "CRM": {
                    "name": "Ringy",
                    "url": "www.ringy.com",
                    "integration_details": {
                        "auth_token": "value1",
                        "sid": "value2"
                        }
                },
                "credentials": {
                    "username": "value1",
                    "password": "value2"
                },
                "campaigns": ["5f9c0a9e9c6d4b1e9c6d4b1e"],
                "custom_fields": {}
            }
        }
    )

    @computed_field
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def to_json(self):
        data = self.model_dump()
        for key, value in data.items():
            if isinstance(value, ObjectId):
                data[key] = str(value)
            elif isinstance(value, list):
                data[key] = [str(v) if isinstance(v, ObjectId) else v for v in value]
                if key == 'balance':
                    data[key] = [{"campaign_id": str(v['campaign_id']), "balance": v['balance']} for v in value]
                elif key == "daily_lead_limit":
                    data[key] = [{"campaign_id": str(v['campaign_id']), "limit": v['limit']} for v in value]
        return data

    async def todays_lead_count(self, campaign_id: str):
        from app.controllers.lead import todays_lead_count_by_agent

        return await todays_lead_count_by_agent(self.id, campaign_id=campaign_id)

    async def campaign_daily_limit(self, campaign_id: ObjectId):
        for campaign in self.daily_lead_limit:
            if campaign.campaign_id == campaign_id:
                return campaign.limit


class UpdateAgentModel(BaseModel):
    """
    A set of optional updates to be made to a Agent document in the database.
    """
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    states_with_license: Optional[List] = None
    CRM: Optional[CRMModel] = Field(default=None)
    created_time: Optional[datetime.datetime] = None
    campaigns: Optional[List[PyObjectId]] = None,
    lead_price_override: Optional[float] = Field(default=None)
    second_chance_lead_price_override: Optional[float] = Field(default=None)
    distribution_type: Optional[str] = Field(default=None)
    credentials: Optional[AgentCredentials] = None
    custom_fields: Optional[dict] = None
    daily_lead_limit: Optional[List[DailyLeadLimit]] = None
    custom_campaign_responses: dict = Field(default_factory=dict)
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "janedoe@example.com",
                "phone": "555-555-5555",
                "states_with_license": ["CA", "NY"],
                "CRM": {
                    "name": "Ringy",
                    "url": "www.ringy.com",
                    "integration_details": {
                        "auth_token": "value1",
                        "sid": "value2"
                        }
                },
                "creation_time": "2020-01-01T00:00:00.000Z",
                "credentials": {
                    "username": "value1",
                    "password": "value2"
                },
                "campaigns": ["5f9c0a9e9c6d4b1e9c6d4b1e", "324sddsds"],
                "custom_fields": {}
            }
        }
    )


class AgentCollection(BaseModel):
    """
    A container holding a list of `AgentModel` instances.

    This exists because providing a top-level array in a JSON response can be a [vulnerability](https://haacked.com/archive/2009/06/25/json-hijacking.aspx/)
    """
    data: List[AgentModel]
