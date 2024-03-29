from bson import ObjectId
from fastapi import APIRouter, Body, status, HTTPException
from fastapi.responses import Response
from pymongo import ReturnDocument

from app.db import db
from app.models.agent import AgentModel, UpdateAgentModel, AgentCollection


router = APIRouter(prefix="/api/agent", tags=["agent"])
agent_collection = db["agent"]


@router.post(
    "/",
    response_description="Add new agent",
    response_model=AgentModel,
    status_code=status.HTTP_201_CREATED,
    response_model_by_alias=False
)
async def create_agent(agent: AgentModel = Body(...)):
    """
    Insert a new agent record.

    A unique `id` will be created and provided in the response.
    """
    new_agent = await agent_collection.insert_one(
        agent.model_dump(by_alias=True, exclude=["id"])
    )
    created_agent = await agent_collection.find_one({"_id": new_agent.inserted_id})
    return created_agent


@router.get(
    "/",
    response_description="Get all agents",
    response_model=AgentCollection,
    response_model_by_alias=False
)
async def list_agents(page: int = 1, limit: int = 10):
    """
    List all of the agent data in the database within the specified page and limit.
    """
    agents = await agent_collection.find().skip((page - 1) * limit).limit(limit).to_list(limit)
    return AgentCollection(agents=agents)


@router.get(
    "/{id}",
    response_description="Get a single agent",
    response_model=AgentModel,
    response_model_by_alias=False
)
async def show_agent(id: str):
    """
    Get the record for a specific agent, looked up by `id`.
    """
    if (
        agent := await agent_collection.find_one({"_id": ObjectId(id)})
    ) is not None:
        return agent

    raise HTTPException(status_code=404, detail=f"Agent {id} not found")


@router.put(
    "/",
    response_description="Update a agent",
    response_model=AgentModel,
    response_model_by_alias=False
)
async def update_agent(id: str, agent: UpdateAgentModel = Body(...)):
    """
    Update individual fields of an existing agent record.

    Only the provided fields will be updated.
    Any missing or `null` fields will be ignored.
    """
    agent = {k: v for k, v in agent.model_dump(by_alias=True).items() if v is not None}

    if len(agent) >= 1:
        update_result = await agent_collection.find_one_and_update(
            {"_id": ObjectId(id)},
            {"$set": agent},
            return_document=ReturnDocument.AFTER,
        )

        if update_result is not None:
            return update_result

        else:
            raise HTTPException(status_code=404, detail=f"Agent {id} not found")

    if (existing_agent := await agent_collection.find_one({"_id": id})) is not None:
        return existing_agent

    raise HTTPException(status_code=404, detail=f"Agent {id} not found")


@router.delete("/", response_description="Delete a agent")
async def delete_agent(id: str):
    """
    Remove a single agent record from the database.
    """
    delete_result = await agent_collection.delete_one({"_id": ObjectId(id)})

    if delete_result.deleted_count == 1:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(status_code=404, detail=f"Agent {id} not found")
