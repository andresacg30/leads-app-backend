from app.db import Database


async def duplication_update():

    campaign_collection = Database().get_db()["campaign"]
    try:
        result = await campaign_collection.update_many(
                    {},  # Match all documents
                    {
                        "$set": {
                            "duplication_cutoff_days": 30
                        }
                    },
                    upsert=True
                )
        print(f"Modified {result.modified_count} documents")
    except Exception as e:
        print(f"An error occurred: {e}")
