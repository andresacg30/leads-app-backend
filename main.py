import asyncio
import os
import stripe
import uvicorn
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.auth.jwt_bearer import JWTBearer
from app.routes import agent, job, lead, campaign, payment, user, transaction, order, webhook, dashboard
from app.routes.lead import public_lead_router
from settings import get_settings

import app.controllers.user as user_controller

import google.cloud.logging


# client = google.cloud.logging.Client()

# client.setup_logging()

app = FastAPI(
    title="LeadConex API"
)

settings = get_settings()

change_stream_task = None

stripe.api_key = settings.stripe_api_key

token_listener = JWTBearer()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(transaction.router)
app.include_router(webhook.router)
app.include_router(user.router, tags=["user"], prefix="/api/user")

app.include_router(public_lead_router)

app.include_router(agent.router, dependencies=[Depends(token_listener)])
app.include_router(lead.router, dependencies=[Depends(token_listener)])
app.include_router(payment.router, dependencies=[Depends(token_listener)])
app.include_router(campaign.router, dependencies=[Depends(token_listener)])
app.include_router(job.router, dependencies=[Depends(token_listener)])
app.include_router(order.router, dependencies=[Depends(token_listener)])
app.include_router(dashboard.router, dependencies=[Depends(token_listener)])


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(user_controller.user_change_stream_listener())


@app.on_event("shutdown")
async def shutdown_event():
    global change_stream_task
    if change_stream_task:
        change_stream_task.cancel()
        try:
            await change_stream_task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    port = os.getenv("PORT")
    if not port:
        port = 8080
    uvicorn.run(app, host="0.0.0.0", port=8080)
