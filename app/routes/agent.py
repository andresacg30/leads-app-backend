import ast
import bson
import json

from typing import List
from fastapi import APIRouter, Body, status, HTTPException, Depends
from fastapi.responses import Response

import app.controllers.agent as agent_controller
import app.controllers.user as user_controller

from app.auth.jwt_bearer import get_current_user
from app.models.agent import AgentModel, UpdateAgentModel, AgentCollection
from app.models.user import UserModel
from app.tools import mappings, formatters


router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/enroll-new-campaign", response_description="Enroll agent in new campaign", response_model_by_alias=False)
async def enroll_agent_in_new_campaign(
    agency_code: str = Body(..., embed=True),
    user: UserModel = Depends(get_current_user)
):
    """
    Enroll agent in new campaign
    """
    from app.controllers.campaign import get_campaigns_by_sign_up_code
    try:
        campaigns = await get_campaigns_by_sign_up_code(agency_code)
        await user_controller.enroll_user_in_campaigns(
            user=user,
            campaigns=campaigns
        )
        for campaign in campaigns:
            try:
                if campaign.id in user.campaigns:
                    raise HTTPException(status_code=400, detail="Agent is already enrolled in this campaign")
                await agent_controller.enroll_agent_in_campaign(
                    agent_id=user.agent_id,
                    campaign_id=campaign.id
                )
            except user_controller.UserNotFoundError as e:
                raise HTTPException(status_code=404, detail=str(e))
            except agent_controller.AgentNotFoundError as e:
                raise HTTPException(status_code=404, detail=str(e))
        return {"message": "Agent enrolled in new campaign"}
    except agent_controller.AgentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.put(
    "/update-daily-limit/{id}",
    response_description="Update daily lead limit for agent",
    response_model_by_alias=False
)
async def update_daily_lead_limit_for_agent(
    id: str,
    daily_lead_limit: int = Body(...),
    campaign_id: str = Body(...),
    user: UserModel = Depends(get_current_user)
):
    """
    Update daily lead limit for agent
    """
    if not user.is_admin():
        raise HTTPException(status_code=404, detail="User does not have permission to update daily lead limit for agent")
    try:
        agent = await agent_controller.get_agent(id=id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        updated_agent = await agent_controller.update_daily_lead_limit(
            agent=agent,
            daily_lead_limit=daily_lead_limit,
            campaign_id=bson.ObjectId(campaign_id)
        )
        return {"id": str(updated_agent["_id"])}
    except agent_controller.AgentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post(
    "/refund-credit",
    response_description="Refund credit to agent",
    response_model_by_alias=False
)
async def refund_credit_to_agent(
    campaign_id: str = Body(...),
    agent_id: str = Body(...),
    amount: float = Body(...),
    distribution_type: str = Body(...),
    user: UserModel = Depends(get_current_user)
):
    """
    Refund credit to agent
    """
    if not agent_id:
        raise HTTPException(status_code=400, detail="Agent id must be provided")
    if user.is_agent():
        raise HTTPException(status_code=404, detail="User does not have permission to refund credit to agent")
    try:
        agent_user = await user_controller.get_user_by_field(agent_id=bson.ObjectId(agent_id))
        if agent_user.is_new_user():
            await user_controller.change_user_permissions(agent_user.id, ["agent"])
        created_transaccion, created_order = await user_controller.refund_credit(
            campaign_id=campaign_id,
            user=agent_user,
            amount=amount,
            distribution_type=distribution_type
        )
        return {"transaction_id": str(created_transaccion.inserted_id), "order_id": str(created_order.inserted_id) if created_order else None}
    except user_controller.UserNotFoundError:
        raise HTTPException(status_code=404, detail="Agent does not have an user associated with it")
    except user_controller.RefundError as e:
        raise HTTPException(status_code=400, detail=str(f"Error refunding: {e}"))


@router.post(
    "/get-eligible-agents-for-lead-processing",
    response_description="Get eligible agent for lead processing based on licensed state and current credit",
    response_model_by_alias=False
)
async def get_eligible_agents_for_lead_processing(
    states: List[str] = Body(...),
    lead_count: int = Body(...),
    second_chance_lead_count: int = Body(...),
    campaign_id: str = Body(...),
    user: UserModel = Depends(get_current_user)
):
    """
    Get eligible agent for lead processing based on licensed state and current credit
    """
    if not states:
        raise HTTPException(status_code=400, detail="States must be provided")
    if not lead_count and not second_chance_lead_count:
        raise HTTPException(status_code=400, detail="Lead count or second chance lead count must be provided")
    formatted_states = [formatters.format_state_to_abbreviation(state) for state in states]
    both_types = False
    if second_chance_lead_count > 0 and lead_count > 0:
        both_types = True
    is_second_chance = second_chance_lead_count > 0
    agents = await agent_controller.get_eligible_agents_for_lead_processing(
        formatted_states,
        lead_count,
        second_chance_lead_count,
        campaign_id=bson.ObjectId(campaign_id),
        is_second_chance=is_second_chance,
        both_types=both_types
    )
    if agents:
        agent_data = list(agent.to_json() for agent in AgentCollection(data=agents).data)
        return {"data": agent_data}
    return {"data": []}


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
            campaigns = {"$in": [bson.ObjectId(campaign) for campaign in user.campaigns]}
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
            agent = AgentModel(**agent_in_db_found)
            await user_controller.create_user_from_agent(agent=agent)
            return {"id": str(agent_in_db_found["_id"])}
    if agent.CRM.name and agent.CRM.name != "null":
        agent.CRM.url = mappings.crm_url_mappings[agent.CRM.name]
    if len(agent.states_with_license) == 1:
        agent.states_with_license = formatters.format_state_list(agent.states_with_license)
    agent.email = agent.email.lower()
    new_agent = await agent_controller.create_agent(agent=agent)
    try:
        agent.id = str(new_agent.inserted_id)
        await user_controller.create_user_from_agent(agent=agent)
    except Exception as e:
        await agent_controller.delete_agent(id=str(new_agent.inserted_id))
        raise HTTPException(status_code=400, detail=str(e))
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
            filter["user_campaigns"] = [bson.ObjectId(campaign) for campaign in user.campaigns]
        sort = [sort.split('=')[0], 1 if sort.split('=')[1] == "ASC" else -1]            
        agents, total = await agent_controller.get_all_agents(page=page, limit=limit, sort=sort, filter=filter, user=user)
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
