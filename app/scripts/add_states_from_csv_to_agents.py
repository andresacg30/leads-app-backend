import pandas as pd
import bson
from pymongo import UpdateOne
from app.db import Database


# State abbreviations dictionary
state_abbreviations = {
    'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA',
    'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE', 'Florida': 'FL', 'Georgia': 'GA',
    'Hawaii': 'HI', 'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA',
    'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
    'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS', 'Missouri': 'MO',
    'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ',
    'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH',
    'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
    'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT',
    'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY'
}

def get_state_abbreviation(state_name):
    """Convert state name to abbreviation"""
    state_name = state_name.strip().title()
    return state_abbreviations.get(state_name, state_name)

async def main():
    agent_collection = Database().get_db()["agent"]

    # Read CSV file
    df = pd.read_csv('agent.csv')
    updates = []
    
    # Process each row in the CSV
    for _, row in df.iterrows():
        agent_id = row['_id']
        states_string = str(row['states_with_license'])
        
        # Split states and convert to abbreviations
        states_list = [get_state_abbreviation(state).upper() for state in states_string.split(',')]
        if states_list == ['']:
            states_list = [state.upper() for state in states_string.split(',')]
        states_list = [s for s in states_list if s]  # Remove empty values
        
        # Update the document in MongoDB
        try:
            updates.append(UpdateOne(
                {"_id": bson.ObjectId(agent_id)},
                {"$set": {"states_with_license": states_list}},
                upsert=True
            ))
            print(f"Updated agent {agent_id} with states: {states_list}")
        except Exception as e:
            print(f"Error updating agent {agent_id}: {str(e)}")
    try:
        if updates:
            await agent_collection.bulk_write(updates)
            print(f"Updated {len(updates)} agents")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()