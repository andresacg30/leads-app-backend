from bson import ObjectId
from fastapi import APIRouter, Body, status, HTTPException
from fastapi.responses import Response
from pymongo import ReturnDocument

import app.controllers.agent as agent_controller

from app.db import db
from app.models.agent import AgentModel, UpdateAgentModel, AgentCollection
from app.tools import mappings


router = APIRouter(prefix="/api/agent", tags=["agent"])
agent_collection = db["agent"]


@router.post(
    "/",
    response_description="Add new agent",
    status_code=status.HTTP_201_CREATED,
    response_model_by_alias=False
)
async def create_agent(agent: AgentModel = Body(...)):
    """
    Insert a new agent record.

    A unique `id` will be created and provided in the response.
    """
    agent_in_db_found = await agent_controller.get_agent_by_email(agent.email)
    if agent_in_db_found:
        agent_in_db_campaigns = await agent_controller.get_enrolled_campaigns(agent_in_db_found['_id'])
        is_duplicate = agent.campaigns[0] in agent_in_db_campaigns
        if is_duplicate:
            raise HTTPException(status_code=409, detail="Agent already exists")
        else:
            agent_in_db_campaigns.append(agent.campaigns[0])
            agent_in_db_found['campaigns'] = agent_in_db_campaigns
            await agent_controller.update_campaigns_for_agent(agent_in_db_found['_id'], agent_in_db_campaigns)
            return agent_in_db_found["_id"]
    agent.CRM.url = mappings.crm_url_mappings[agent.CRM.name]
    if len(agent.states_with_license) == 1:
        agent.states_with_license = agent_controller.format_state_list(agent.states_with_license)
    new_agent = await agent_collection.insert_one(
        agent.model_dump(by_alias=True, exclude=["id"])
    )
    return {"id": str(new_agent.inserted_id)}


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
        return {"id": existing_agent['_id']}

    raise HTTPException(status_code=404, detail=f"Agent {id} not found")


@router.delete("/", response_description="Delete a agent")
async def delete_agent(id: str):
    """
    Remove a single agent record from the database.
    """
    delete_result = await agent_collection.delete_one({"_id": ObjectId(id)})  # make it a controller

    if delete_result.deleted_count == 1:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(status_code=404, detail=f"Agent {id} not found")


@router.get(
    "/get-agent-id-by-email/{email}",
    response_description="Get agent id by email",
    response_model_by_alias=False
)
async def get_agent_id_by_email(email: str):
    """
    Get the record for a specific agent, looked up by `email`.
    """
    agent = await agent_controller.get_agent_by_email(email)
    if agent:
        return {"id": str(agent["_id"])}
    raise HTTPException(status_code=404, detail=f"Agent {email} not found")
