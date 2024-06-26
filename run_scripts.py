import app.scripts.agents_import as agents_import
import app.scripts.leads_import as leads_import
import sys
import asyncio


if __name__ == "__main__":
    file = sys.argv[1]
    db_collection = sys.argv[2]
    asyncio.run(agents_import.import_csv(file, db_collection))
