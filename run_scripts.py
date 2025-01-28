import app.scripts.add_duplication_cutoff_days_to_campaign as duplication_script
import asyncio


if __name__ == "__main__":
    asyncio.run(duplication_script.duplication_update())
