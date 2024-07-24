import datetime
import re
import sys
import pandas as pd

from pymongo import UpdateOne
from bson import ObjectId
from zoneinfo import ZoneInfo

from app.db import db
from app.models.lead import LeadModel
from app.tools.mappings import state_mappings
from app.models.agent import PyObjectId


sys.path.append('../../app')


def format_time(time):
    if pd.isna(time):
        return None
    if re.fullmatch(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}", time):
        date, time_part = time.split(' ')
        month, day, year = map(int, date.split('/'))
        time = f"{year:04d}-{month:02d}-{day:02d}T{time_part}.000"
    elif re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{3}Z", time):
        time = time[:-1]
    elif re.fullmatch(r"\d{2}-\d{2}-\d{4}", time):
        month, day, year = map(int, time.split('-'))
        time = f"{year:04d}-{month:02d}-{day:02d}T00:00:00.000"
    elif re.fullmatch(r"\d{1,2}/\d{1,2}/\d{2,4}", time):
        month, day, year = map(int, time.split('/'))
        time = f"{year:04d}-{month:02d}-{day:02d}T00:00:00.000"
    try:
        dt = datetime.datetime.fromisoformat(time)
        est_time = dt.astimezone(ZoneInfo("US/Eastern"))
        utc_time = est_time.astimezone(ZoneInfo("UTC"))
        return utc_time
    except Exception as e:
        print(f"{e}")


def format_state(state):
    try:
        for formatted_state, state_variations in state_mappings.items():
            if state.lower() in state_variations:
                return formatted_state
    except Exception:
        print(f"Error while formatting state {state}")


def format_custom_fields(row, start_column=12):
    headers = row.index

    relevant_values = row.iloc[start_column - 1:]
    relevant_headers = headers[start_column - 1:]

    extra_fields = dict(zip(relevant_headers, relevant_values))

    return extra_fields


def format_lead(lead):
    custom_fields_dict = format_custom_fields(lead)
    formatted_lead = {}
    formatted_lead['first_name'] = lead["first_name"] if not pd.isna(lead["first_name"]) else ""
    formatted_lead["last_name"] = lead["last_name"] if not pd.isna(lead["last_name"]) else ""
    formatted_lead["email"] = str(lead["email"]).strip() if not pd.isna(lead["email"]) else "noemail@leadconex.com"
    formatted_lead["phone"] = str(lead["phone"]) if not pd.isna(lead["phone"]) else ""
    formatted_lead["created_time"] = format_time(lead["created_time"])
    formatted_lead["campaign_id"] = lead["campaign_id"]
    formatted_lead["state"] = format_state(lead["state"].lstrip().rstrip()) if not pd.isna(lead["state"]) else ""
    formatted_lead["custom_fields"] = custom_fields_dict
    formatted_lead["origin"] = "facebook"
    if not pd.isna(lead["buyer_id"]) :
        formatted_lead["buyer_id"] = PyObjectId(str(lead["buyer_id"]))
        formatted_lead["lead_sold_time"] = format_time(lead["lead_sold_time"])
    if not pd.isna(lead["second_chance_buyer_id"]):
        formatted_lead["second_chance_buyer_id"] = PyObjectId(str(lead["second_chance_buyer_id"]))
        formatted_lead["second_chance_lead_sold_time"] = format_time(lead["second_chance_lead_sold_time"])
    try:
        lead = LeadModel(**formatted_lead)
    except Exception as e:
        raise Exception(f"Error while formatting lead {formatted_lead.get('email')}")
    return lead


async def send_to_db(file, db_collection):
    leads = pd.read_csv(file)
    leads_to_insert = []
    for _, lead in leads.iterrows():
        formatted_lead = format_lead(lead)
        leads_to_insert.append(formatted_lead.model_dump(by_alias=True, exclude=["id"]))
        #filter_condition = {"_id": ObjectId(formatted_lead.id)}
        #operations.append(UpdateOne(filter_condition, {"$set": formatted_lead.model_dump(by_alias=True, exclude=["id"])}, upsert=True))
    try:
        collection = db[db_collection]
        await collection.insert_many(leads_to_insert)
    except Exception as e:
        print(f"Error while sending to db {e}")
