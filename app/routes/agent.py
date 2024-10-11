import ast
import json

from typing import List
from fastapi import APIRouter, Body, status, HTTPException, Depends
from fastapi.responses import Response

import app.controllers.agent as agent_controller
import app.controllers.campaign as campaign_controller

from app.auth.jwt_bearer import get_current_user
from app.models.agent import AgentModel, UpdateAgentModel, AgentCollection
from app.models.user import UserModel
from app.tools import mappings, formatters


router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.get(
    "/find",
    response_description="Get agent id by specified field",
    response_model_by_alias=False
)
async def get_agent_id_by_field(
    email: str = None,
    phone: str = None,
    first_name: str = None,
    last_name: str = None,
    full_name: str = None,
    user: UserModel = Depends(get_current_user)
):
    """
    Get the id for a specific agent, looked up by a specified field.
    """
    if first_name and not last_name or last_name and not first_name:
        raise HTTPException(status_code=400, detail="First name and last name must be provided together")
    try:
        if not user.is_admin():
            campaigns = {"$in": user.campaigns}
        else:
            campaigns = None
        if email:
            email = email.lower()
        agent = await agent_controller.get_agent_by_field(
            email=email,
            phone=phone,
            first_name=first_name,
            last_name=last_name,
            full_name=full_name,
            campaigns=campaigns
        )
        return {"id": str(agent["_id"])}
    except agent_controller.AgentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/get-active",
    response_description="Get active agents",
    response_model_by_alias=False
)
async def get_active_agents(user: UserModel = Depends(get_current_user)):
    """
    Get the record for all active agents.
    """
    if not user.is_admin():
        if not user.campaigns:
            raise HTTPException(status_code=404, detail="User does not have access to this campaign")
    if user.is_admin():
        campaigns = await campaign_controller.get_campaign_collection().find().to_list(None)
        campaign_ids = [str(campaign["_id"]) for campaign in campaigns]
        user.campaigns = campaign_ids
    agents, total = await agent_controller.get_active_agents(user_campaigns=user.campaigns)
    return {"data": agents, "total": total}


@router.post(
    "/get-many",
    response_description="Get multiple agents",
    response_model_by_alias=False
)
async def get_multiple_agents(ids: List[str] = Body(...)):
    """
    Get the record for multiple agents, looked up by `ids`.
    """
    try:
        agents = await agent_controller.get_agents(ids)
        return {"data": list(agent.to_json() for agent in AgentCollection(data=agents).data)}
    except agent_controller.AgentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post(
    "",
    response_description="Add new agent",
    status_code=status.HTTP_201_CREATED,
    response_model_by_alias=False
)
async def create_agent(agent: AgentModel = Body(...), user: UserModel = Depends(get_current_user)):
    """
    Insert a new agent record.

    A unique `id` will be created and provided in the response.
    """
    try:
        if not user.is_admin():
            raise HTTPException(status_code=404, detail="User do not have permission to create agents")
        agent_in_db_found = await agent_controller.get_agent_by_field(email=agent.email)
    except agent_controller.AgentNotFoundError:
        agent_in_db_found = None
    if agent_in_db_found:
        agent_in_db_campaigns = await agent_controller.get_enrolled_campaigns(agent_in_db_found['_id'])
        is_duplicate = agent.campaigns[0] in agent_in_db_campaigns
        if is_duplicate:
            raise HTTPException(status_code=409, detail="Agent already exists")
        else:
            agent_in_db_campaigns.append(agent.campaigns[0])
            agent_in_db_found['campaigns'] = agent_in_db_campaigns
            await agent_controller.update_campaigns_for_agent(agent_in_db_found['_id'], agent_in_db_campaigns)
            return {"id": str(agent_in_db_found["_id"])}
    agent.CRM.url = mappings.crm_url_mappings[agent.CRM.name]
    if len(agent.states_with_license) == 1:
        agent.states_with_license = formatters.format_state_list(agent.states_with_license)
    agent.email = agent.email.lower()
    new_agent = await agent_controller.create_agent(agent=agent)
    return {"id": str(new_agent.inserted_id)}


@router.get(
    "",
    response_description="Get all agents",
    response_model_by_alias=False
)
async def list_agents(
    page: int = 1,
    limit: int = 10,
    sort: str = "created_time=DESC",
    filter: str = None,
    user: UserModel = Depends(get_current_user)
):
    """
    List all of the agent data in the database within the specified page and limit.
    """
    if sort.split('=')[1] not in ["ASC", "DESC"]:
        raise HTTPException(status_code=400, detail="Invalid sort parameter")
    try:
        filter = ast.literal_eval(filter) if filter else None
        if not user.is_admin():
            if not filter:
                filter = {}
            if not user.campaigns:
                raise HTTPException(status_code=404, detail="User does not have access to this campaign")
            filter["user_campaigns"] = user.campaigns
        sort = [sort.split('=')[0], 1 if sort.split('=')[1] == "ASC" else -1]
        agents, total = await agent_controller.get_all_agents(page=page, limit=limit, sort=sort, filter=filter)
        return {"data": list(agent.to_json() for agent in AgentCollection(data=agents).data), "total": total}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/{id}",
    response_description="Get a single agent",
    response_model_by_alias=False
)
async def show_agent(id: str, user: UserModel = Depends(get_current_user)):
    """
    Get the record for a specific agent, looked up by `id`.
    """
    if not user.is_admin():
        if not user.campaigns:
            raise HTTPException(status_code=404, detail="User does not have access to this agent")
    if (
        agent := await agent_controller.get_agent(id=id)
    ) is not None:
        if not user.is_admin():
            for campaign in agent.campaigns:
                if campaign not in user.campaigns:
                    agent.campaigns.remove(campaign)
            if len(agent.campaigns) == 0:
                raise HTTPException(status_code=404, detail="User does not have access to this agent")
        return agent.to_json()

    raise HTTPException(status_code=404, detail=f"Agent {id} not found")


@router.put(
    "/{id}",
    response_description="Update a agent",
    response_model_by_alias=False
)
async def update_agent(id: str, agent: UpdateAgentModel = Body(...), user: UserModel = Depends(get_current_user)):
    """
    Update individual fields of an existing agent record.

    Only the provided fields will be updated.
    Any missing or `null` fields will be ignored.
    """
    if not user.is_admin():
        allowed_fields = ["email", "phone", "first_name", "last_name", "CRM", "states_with_license"]
        if not any([v for k, v in agent.dict(by_alias=True).items() if k in allowed_fields]):
            raise HTTPException(status_code=403, detail="User does not have permission to update this agent")
    try:
        if agent.email:
            agent.email = agent.email.lower()
        updated_agent = await agent_controller.update_agent(id, agent)
        return {"id": str(updated_agent["_id"])}

    except agent_controller.AgentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except agent_controller.AgentIdInvalidError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except agent_controller.AgentEmptyError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{id}", response_description="Delete a agent")
async def delete_agent(id: str, user: UserModel = Depends(get_current_user)):
    """
    Remove a single agent record from the database.
    """
    if not user.is_admin():
        raise HTTPException(status_code=404, detail="User does not have permission to delete this agent")
    if len(id.split(",")) > 1:
        id = id.split(",")
        delete_result = await agent_controller.delete_agents(ids=id)
        if delete_result.deleted_count >= 1:
            return Response(status_code=status.HTTP_204_NO_CONTENT, content=json.dumps({"data": "Agents deleted"}))
    delete_result = await agent_controller.delete_agent(id=id)

    if delete_result.deleted_count == 1:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(status_code=404, detail=f"Agent {id} not found")
