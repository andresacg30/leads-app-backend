import os
import uvicorn
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.auth.jwt_bearer import JWTBearer
from app.routes import agent, lead, invoice, campaign, user


app = FastAPI(
    title="LeadConex API"
)

token_listener = JWTBearer()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(user.router, tags=["user"], prefix="/api/user")
app.include_router(agent.router, dependencies=[Depends(token_listener)])
app.include_router(lead.router, dependencies=[Depends(token_listener)])
app.include_router(invoice.router, dependencies=[Depends(token_listener)])
app.include_router(campaign.router, dependencies=[Depends(token_listener)])


if __name__ == "__main__":
    port = os.getenv("PORT")
    if not port:
        port = 8080
    uvicorn.run(app, host="0.0.0.0", port=8080)
