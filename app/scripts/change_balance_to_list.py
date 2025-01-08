from bson import ObjectId
from pymongo import UpdateOne


async def update_user_balance():
    from app.controllers.user import get_user_collection

    users_collection = get_user_collection()
    updates = []

    users = await users_collection.find().to_list(None)

    for user in users:
        current_balance = user.get("balance", 0.0)

        campaigns = user.get("campaigns")
        if not campaigns:
            continue
        new_balance = [
            {"campaign_id": ObjectId(campaigns[0]),
             "balance": current_balance}
        ]

        updates.append(UpdateOne(
            {"_id": user.get("_id")},
            {"$set": {"balance": new_balance}}
        ))

    result = await users_collection.bulk_write(updates)
    print(f"User balances updated successfully. Result: {result}")


async def update_agent_balance():
    from app.controllers.agent import get_agent_collection

    agents_collection = get_agent_collection()
    updates = []

    agents = await agents_collection.find().to_list(None)

    for agent in agents:
        current_balance = agent.get("balance", 0.0)

        campaigns = agent.get("campaigns")
        if not campaigns:
            continue
        new_balance = [
            {"campaign_id": ObjectId(campaigns[0]),
             "balance": current_balance}
        ]

        updates.append(UpdateOne(
            {"_id": agent.get("_id")},
            {"$set": {"balance": new_balance}}
        ))

    result = await agents_collection.bulk_write(updates)
    print(f"Agent balances updated successfully. Result: {result}")
    
    
async def fix_user_balance():
    from app.controllers.user import get_user_collection
    
    users_collection = get_user_collection()
    updates = []
    
    users = await users_collection.find().to_list(None)
    
    for user in users:
        balance = user.get("balance", [])
        if not balance or not isinstance(balance, list):
            continue
            
        first_balance = balance[0]
        if isinstance(first_balance.get("balance"), list):
            # Fix the nested balance
            correct_balance = first_balance["balance"][0]["balance"]
            new_balance = [{"campaign_id": first_balance["campaign_id"], "balance": correct_balance}]
            
            updates.append(UpdateOne(
                {"_id": user.get("_id")},
                {"$set": {"balance": new_balance}}
            ))
    
    if updates:
        result = await users_collection.bulk_write(updates)
        print(f"User balances fixed successfully. Result: {result}")
    else:
        print("No balances needed fixing")
    
    