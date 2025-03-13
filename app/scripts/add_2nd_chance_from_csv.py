import csv
from bson import ObjectId
from typing import List, Dict
import pandas as pd
from app.controllers.lead import get_lead_collection
from app.models.lead import LeadModel
from pymongo import InsertOne
from app.tools.formatters import get_full_state_name  # Import the utility function


def process_csv_to_leads(file_path: str) -> List[Dict]:
    # Read CSV file using pandas
    df = pd.read_csv(file_path)
    
    # Get standard field names and custom field names
    standard_fields = ['Email', 'State', 'Full Name', 'Phone']
    custom_fields = [col for col in df.columns if col not in standard_fields]
    
    operations = []
    
    # Iterate through rows and create update operations
    for _, row in df.iterrows():
        # Split NAME into first_name and last_name
        name_parts = str(row['Full Name']).split()
        first_name = name_parts[0] if name_parts else ""
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
        
        # Standardize state to full name
        try:
            state = get_full_state_name(row['State'])
        except (AttributeError, KeyError):
            # Fallback if state lookup fails
            state = row['State']
            print(f"Warning: Could not standardize state '{state}' for {row['Email']}")

        # Create lead document
        lead_doc = {
            "email": row['Email'],
            "state": state,
            "first_name": first_name,
            "last_name": last_name,
            "phone": row['Phone'],
            "is_second_chance": True,
            "custom_fields": {},
            "origin": "csv",
            "campaign_id": "67bf5e5e40df211069c97a7a"
        }
        # Add custom fields
        for field in custom_fields:
            if pd.notna(row[field]):  # Check if value is not NaN
                lead_doc["custom_fields"][field] = row[field]
        
        lead = LeadModel(**lead_doc)
        del lead.id
        lead_to_push = lead.to_json()
        lead_to_push["campaign_id"] = lead.campaign_id

        operations.append(InsertOne(
            lead_to_push  # Use lead_to_push which has ObjectId properly set
        ))
    
    return operations


async def main():
    file_path = "
    operations = process_csv_to_leads(file_path)
    
    lead_collection = get_lead_collection()
    result = await lead_collection.bulk_write(operations)

    print(f"Inserted {result.inserted_count} documents")