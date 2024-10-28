import asyncio
import os
import stripe
import uvicorn
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.auth.jwt_bearer import JWTBearer
from app.routes import agent, lead, campaign, payment, user, transaction
from settings import get_settings

from app.controllers.user import user_change_stream_listener


app = FastAPI(
    title="LeadConex API"
)

settings = get_settings()

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
app.include_router(user.router, tags=["user"], prefix="/api/user")
app.include_router(agent.router, dependencies=[Depends(token_listener)])
app.include_router(lead.router, dependencies=[Depends(token_listener)])
app.include_router(payment.router, dependencies=[Depends(token_listener)])
app.include_router(campaign.router, dependencies=[Depends(token_listener)])


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(user_change_stream_listener())


if __name__ == "__main__":
    port = os.getenv("PORT")
    if not port:
        port = 8080
    uvicorn.run(app, host="0.0.0.0", port=8080)
