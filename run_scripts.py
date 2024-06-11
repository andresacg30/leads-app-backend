import app.scripts as scripts
import sys
import asyncio


if __name__ == "__main__":
    file = sys.argv[1]
    db_collection = sys.argv[2]
    asyncio.run(scripts.import_csv(file, db_collection))
