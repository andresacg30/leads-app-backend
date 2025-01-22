
async def main():
    from app.controllers.user import get_user_collection

    user_collection = get_user_collection()
    try:
        # If subscription_details does not exist, set it to the new schema
        result = await user_collection.update_many(
                    {},  # Match all documents
                    {
                        "$set": {
                            "subscription_details": {
                                "current_subscriptions": [],
                                "past_subscriptions": []
                            }
                        }
                    },
                    upsert=True  # Create if doesn't exist, update if exists
                )
        print(f"Modified {result.modified_count} documents")
    except Exception as e:
        print(f"An error occurred: {e}")
