import datetime
import re
import sys
import pandas as pd

from zoneinfo import ZoneInfo

from app.models.lead import LeadModel
from app.tools.mappings import state_mappings


sys.path.append('../../app')


def format_time(time):
    if re.fullmatch("\d{4}-\d{2}-\d{2}", time):
        time = time + "T00:00:00.000"
    est_time = datetime.datetime.fromisoformat(time).astimezone(ZoneInfo("US/Eastern"))
    utc_time = est_time.astimezone(ZoneInfo("UTC"))
    formatted_time = utc_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    return formatted_time


def format_state(state):
    formatted_state = state_mappings.get(state)
    return formatted_state


def format_custom_fields(row, start_column=12):
    headers = row.index

    relevant_values = row.iloc[start_column - 1:]
    relevant_headers = headers[start_column - 1:]

    extra_fields = dict(zip(relevant_headers, relevant_values))

    return extra_fields


def format_lead(lead):
    formatted_lead = {}
    formatted_lead.first_name = lead["first_name"]
    formatted_lead.last_name = lead["last_name"] if lead["last_name"] else ""
    formatted_lead.email = lead["email"]
    formatted_lead.phone = lead["phone"]
    formatted_lead["created_time"] = format_time(lead["created_time"])
    formatted_lead["campaign_id"] = lead["campaign_id"]
    formatted_lead["state"] = format_state(lead["state"])
    formatted_lead["custom_fields"] = format_custom_fields(lead["custom_fields"])
    if "buyer_id" in lead:
        formatted_lead["buyer_id"] = lead["buyer_id"]
        formatted_lead["lead_sold_time"] = format_time(lead["lead_sold_time"])
    if "second_chance_buyer_id" in lead:
        formatted_lead["second_chance_buyer_id"] = lead["second_chance_buyer_id"]
        formatted_lead["second_chance_lead_sold_time"] = format_time(lead["second_chance_lead_sold_time"])
    return formatted_lead
    

def send_to_db():
    file = open("leads.csv")
    leads = pd.read_csv(file)
    leads_to_insert = []
    for _, lead in leads:
        formatted_lead = format_lead(lead)
        leads_to_insert.append(formatted_lead.model_dump(by_alias=True, exclude=["id"]))
    leads_to_insert.insert_many(leads_to_insert)

