from app.db import Database
from pymongo import UpdateMany


async def add_priority_field_to_orders():
    order_collection = Database().get_db()["order"]
    try:
        orders = await order_collection.find({"priority": {"$exists": False}}).to_list(None)

        default_priority = {
            "duration": 0,
            "start_time": None,
            "end_time": None,
            "active": False
        }

        updates = []
        for order in orders:
            updates.append(UpdateMany(
                {"_id": order["_id"]},
                {"$set": {"priority": default_priority}},
                upsert=False
            ))

        if updates:
            result = await order_collection.bulk_write(updates)
            print(f"Priority field added to {result.modified_count} orders")
        else:
            print("No orders found without priority field")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("Priority field update completed")


async def main():
    await add_priority_field_to_orders()
