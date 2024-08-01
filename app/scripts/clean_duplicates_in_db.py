from app.db import db


async def clean_duplicates_by_email_and_buyer_id():
    leads = db["lead"]
    campaign_id = "6668b634a88f8e5a8dde197c"
    cursor = leads.aggregate(
        [ 
            {"$match": {"campaign_id": campaign_id}},
            {
                "$group": {
                    "_id": {"email": "$email", "buyer_id": "$buyer_id", "lead_sold_time": "$lead_sold_time"},
                    "duplicates": {"$push": "$_id"},
                    "count": {"$sum": 1},
                }
            },
            {"$match": {"count": {"$gt": 1}}},
        ]
    )
    counter = 0

    async for doc in cursor:
        db.lead.delete_many({"_id": {"$in": doc["duplicates"][1:]}})
        for duplicate in doc["duplicates"][1:]:
            counter += 1
    print(counter)
