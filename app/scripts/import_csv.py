from app.models import agent, lead, crm, invoice, campaigns



def clean_data_for_agent_model(data):
    agent_list = []
    for _, row in agent_data.iterrows():
        agent_to_clean = agent.AgentModel(
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
def clean_data_for_crm_model(data):
    pass

collection_model_mapping = {
    "agent": clean_data_for_agent_model,
    "crm": clean_data_for_crm_model
}

def clean_data(db_collection, file):
    function = collection_model_mapping.get(db_collection)
    cleaned_data = function(file)
    return cleaned_data
    

def import_csv(file, db_collection):
    data = clean_data(db_collection, file)  # cleaned data
    """
    data: {
        name: something,
        last_name...
        phone: 40456156 or ""
    }
    """
    db_collection.insert_many(data)