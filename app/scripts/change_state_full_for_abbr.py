from pymongo import UpdateMany
from app.db import Database

state_map = {
    "Alabama": "AL",
    "Alaska": "AK",
    "Arizona": "AZ",
    "Arkansas": "AR",
    "California": "CA",
    "Colorado": "CO",
    "Connecticut": "CT",
    "Delaware": "DE",
    "Florida": "FL",
    "Georgia": "GA",
    "Hawaii": "HI",
    "Idaho": "ID",
    "Illinois": "IL",
    "Indiana": "IN",
    "Iowa": "IA",
    "Kansas": "KS",
    "Kentucky": "KY",
    "Louisiana": "LA",
    "Maine": "ME",
    "Maryland": "MD",
    "Massachusetts": "MA",
    "Michigan": "MI",
    "Minnesota": "MN",
    "Mississippi": "MS",
    "Missouri": "MO",
    "Montana": "MT",
    "Nebraska": "NE",
    "Nevada": "NV",
    "New Hampshire": "NH",
    "New Jersey": "NJ",
    "New Mexico": "NM",
    "New York": "NY",
    "North Carolina": "NC",
    "North Dakota": "ND",
    "Ohio": "OH",
    "Oklahoma": "OK",
    "Oregon": "OR",
    "Pennsylvania": "PA",
    "Rhode Island": "RI",
    "South Carolina": "SC",
    "South Dakota": "SD",
    "Tennessee": "TN",
    "Texas": "TX",
    "Utah": "UT",
    "Vermont": "VT",
    "Virginia": "VA",
    "Washington": "WA",
    "West Virginia": "WV",
    "Wisconsin": "WI",
    "Wyoming": "WY"
}


async def change_state_full_for_abbr():
    agent_collection = Database().get_db()["agent"]
    try:
        agents = await agent_collection.find({}).to_list(None)
        updates = []
        for agent in agents:
            states_with_license = agent.get("states_with_license")
            new_states = []
            for state in states_with_license:
                if state and len(state) > 2:  # Only process full state names
                    abbr = state_map.get(state)
                    if abbr:  # Only update if we have a valid mapping
                        new_states.append(abbr)
            updates.append(
                UpdateMany(
                    {"_id": agent["_id"]},
                    {"$set": {"states_with_license": new_states}},
                    upsert=True
                )
            )
        if updates:
            await agent_collection.bulk_write(updates)
            print(f"Updated {len(updates)} agents, {agents}")
        else:
            print(f"{agents}")
    except Exception as e:
        print(f"An error occurred: {e}")
