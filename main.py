import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import agent, lead, invoice, campaign


app = FastAPI(
    title="LeadConex API"
)
app.include_router(agent.router)
app.include_router(lead.router)
app.include_router(invoice.router)
app.include_router(campaign.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # List of allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


if __name__ == "__main__":
    port = os.getenv("PORT")
    if not port:
        port = 8080
    uvicorn.run(app, host="0.0.0.0", port=8080)
