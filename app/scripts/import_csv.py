import pandas as pd
import sys

from bson import ObjectId
from datetime import datetime

from app.models import agent, lead, campaigns
from app.models.agent import PyObjectId, AgentCredentials, CRMModel
from app.db import db


sys.path.append('../../app')


async def clean_data_for_agent_model(data):
    agent_list = []
    for _, row in data.iterrows():
        try:
            row['Email'] = str(row['Email']).strip()
            row['campaign_id'] = str(row['campaign_id']).strip()
            agent_query: dict = await db["agent"].find_one(
                {"email": {"$regex": row['Email'], "$options": "i"}}
            )
            if agent_query != None:
                existing_campaigns = set(agent_query['campaigns'])
                updated_campaigns = list(existing_campaigns | {row['campaign_id']})
                agent_query['campaigns'] = updated_campaigns
                agent_id = agent_query['_id']
                del agent_query["_id"]
                await db["agent"].update_one({"_id": ObjectId(agent_id)}, {"$set": agent_query})
            else:
                integration_details = extract_extra_fields_for_lead(row, 12)
                agent_to_clean = agent.AgentModel(
                    first_name=str(row['First Name']),
                    last_name=str(row['Last Name']),
                    email=row['Email'],
                    phone=str(row['Phone']) if not pd.isna(row['Phone']) else '',
                    states_with_license=row['What states do you want leads in?'].split(',') if not pd.isna(row['What states do you want leads in?']) else [],
                    CRM=CRMModel(
                        name=row['Which CRM Do You Use?'] if not pd.isna(row['Which CRM Do You Use?']) else '',
                        url=row['URL'] if not pd.isna(row['URL']) else '',
                        integration_details=integration_details
                    ),
                    created_time=pd.to_datetime(row['Created']),
                    campaigns=[row['campaign_id']],
                    credentials=AgentCredentials(
                        id_token=row['Username'] if not pd.isna(row['Username']) else '',
                        password=row['Password'] if not pd.isna(row['Password']) else ''
                        )
                    )
                agent_list.append(agent_to_clean.model_dump(by_alias=True, exclude=["id"]))
        except Exception as e:
            print("Error while cleaning agent model. Error: {}".format(e))
    return agent_list


async def clean_data_for_campaign_model(data):
    campaign_list = []
    for _, row in data.iterrows():
        try:
            campaign_to_clean = campaigns.CampaignModel(
                name=str(row['name']),
                active=bool(row['active']),
                start_date=pd.to_datetime(row['start_date']),
            )
            await campaign_list.append(campaign_to_clean.model_dump(by_alias=True, exclude=["id"]))
        except Exception as e:
            print("Error while cleaning campaign model. Error: {}".format(e))
    return campaign_list


def clean_data_for_lead_model(data):
    lead_list = []
    for _, row in data.iterrows():
        try:
            custom_fields_dict = extract_extra_fields_for_lead(row, 14)
            lead_to_clean = lead.LeadModel(
                first_name=str(row['first_name']),
                last_name=str(row['last_name']) if not pd.isna(row['last_name']) else '',
                email=str(row['email']),
                phone=str(row['phone']),
                state=str(row['state']),
                origin=str(row['origin']),
                buyer_id=PyObjectId(str(row['buyer_id'])),
                second_chance_buyer_id=PyObjectId(str(row['second_chance_buyer_id'])),
                created_time=pd.to_datetime(row['created_time']) if not pd.isna(row['created_time']) else datetime.utcnow(),
                lead_sold_time=pd.to_datetime(row['lead_sold_time']) if not pd.isna(row['lead_sold_time']) else None,
                second_chance_lead_sold_time=pd.to_datetime(row['second_chance_lead_sold_time']) if not pd.isna(row['second_chance_lead_sold_time']) else None,
                campaign_id=PyObjectId(str(row['campaign_id'])),
                is_second_chance=bool(row['is_second_chance']),
                custom_fields=custom_fields_dict
            )
            lead_list.append(lead_to_clean.model_dump(by_alias=True, exclude=["id"]))
        except Exception as e:
            print("Error while cleaning lead model. Error: {}".format(e))
    return lead_list

collection_model_mapping = {
    "agent": clean_data_for_agent_model,
    "campaign": clean_data_for_campaign_model,
    "lead": clean_data_for_lead_model
}

async def clean_data(db_collection, file):
    try:
        df = pd.read_csv(file)
        function = collection_model_mapping.get(db_collection)
        if function:
            cleaned_data = await function(df)
            return cleaned_data
        else:
            ("Function not found for {}".format(db_collection))
            return None
    except Exception as e:
        print("Error while cleaning data:")
    
def extract_extra_fields_for_lead(row, start_column):
    headers = row.index

    relevant_values = filter(row.iloc[start_column - 1:], lambda x: x != None)
    relevant_headers = headers[start_column - 1:]

    extra_fields = dict(zip(relevant_headers, relevant_values))

    return extra_fields

async def import_csv(file, db_collection):
    try:
        data = await clean_data(db_collection, file)  # cleaned data
        if data:
            collection = db[db_collection]
            await collection.insert_many(data)
        else:
            print("No data to import.")
    except Exception as e:
        print(f"Error importing CSV data: {e}")
