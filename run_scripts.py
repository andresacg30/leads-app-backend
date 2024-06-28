import app.scripts.agents_import as agents_import
import app.scripts.leads_import as leads_import
import sys
import asyncio


if __name__ == "__main__":
    file = input("file:")
    db_collection = input("db_collection: ")
    # asyncio.run(agents_import.import_csv(file, db_collection))
    asyncio.run(leads_import.send_to_db(file, db_collection))
