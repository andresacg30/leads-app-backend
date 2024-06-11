import os
import uvicorn
from fastapi import FastAPI

from app.routes import agent, lead, invoice

app = FastAPI(
    title="LeadConex API"
)
app.include_router(agent.router)
app.include_router(lead.router)
app.include_router(invoice.router)


if __name__ == "__main__":
    port = os.getenv("PORT")
    if not port:
        port = 8080
    uvicorn.run(app, host="0.0.0.0", port=8080)
