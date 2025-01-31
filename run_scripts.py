import app.scripts.add_daily_lead_limit_to_agents as daily_lead_limit_script
import asyncio


if __name__ == "__main__":
    asyncio.run(daily_lead_limit_script.daily_lead_limit_creation())
