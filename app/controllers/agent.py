#TODO:import_csv(): Function that reads our current system's data and migrate it to our new database. Use pandas.

#TODO: add new info to database on current systems. We need prod for this.

import pandas as pd
from pymongo import MongoClient
import sys
sys.path.append('../../app')
from models.agent import AgentModel, AgentCredentials, PyObjectId

agent_data = pd.read_csv("../../CSV/Agents/IUL_Agents_Final.csv") #adjust path as needed
agent_list = []

for _, row in agent_data.iterrows():
    agent = AgentModel(
        id=PyObjectId(str(row['Contact Id'])),
        first_name=str(row['First Name']),
        last_name=str(row['Last Name']),
        email=row['Email'],
        phone=str(row['Phone']) if not pd.isna(row['Phone']) else '',
        states_with_license=row['What states do you want leads in?'].split(',') if not pd.isna(row['What states do you want leads in?']) else [],
        CRM=row['Which CRM Do You Use?'] if not pd.isna(row['Which CRM Do You Use?']) else None,
        created_time=pd.to_datetime(row['Created']),
        campaigns=["Capital Financial Solutions"],  #don't forget to change campaign name
        credentials=AgentCredentials(
            id_token=row['Username'] if not pd.isna(row['Username']) else '',
            password=row['Password'] if not pd.isna(row['Password']) else ''
        )
    )
    agent_list.append(agent)

client = MongoClient('mongodb+srv://leadconex:Family321!@leadconex.cwcg2ii.mongodb.net/?retryWrites=true&w=majority&appName=LeadConex')
db = client['LeadConex']
collection = db['Capital Financial Agents'] #don't forget to change collection name

for agent in agent_list:
    inserted_data = collection.insert_one(agent.model_dump(by_alias=True))
    print(f"{agent.first_name} {agent.last_name} inserted with ID: {inserted_data.inserted_id}")

