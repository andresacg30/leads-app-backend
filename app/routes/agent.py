from fastapi import APIRouter, Body, status, HTTPException
from fastapi.responses import Response

import app.controllers.agent as agent_controller

from app.models.agent import AgentModel, UpdateAgentModel, AgentCollection
from app.tools import mappings, formatters


router = APIRouter(prefix="/api/agent", tags=["agent"])


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
    try:
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
    new_agent = await agent_controller.create_agent(agent=agent)
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
    agents = await agent_controller.get_all_agents(page=page, limit=limit)
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
        agent := await agent_controller.get_agent(id=id)
    ) is not None:
        return agent

    raise HTTPException(status_code=404, detail=f"Agent {id} not found")


@router.put(
    "/{id}",
    response_description="Update a agent",
    response_model_by_alias=False
)
async def update_agent(id: str, agent: UpdateAgentModel = Body(...)):
    """
    Update individual fields of an existing agent record.

    Only the provided fields will be updated.
    Any missing or `null` fields will be ignored.
    """
    try:
        updated_agent = await agent_controller.update_agent(id, agent)
        return {"id": str(updated_agent["_id"])}

    except agent_controller.AgentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except agent_controller.AgentIdInvalidError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except agent_controller.EmptyAgentError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{id}", response_description="Delete a agent")
async def delete_agent(id: str):
    """
    Remove a single agent record from the database.
    """
    delete_result = await agent_controller.delete_agent(id=id)

    if delete_result.deleted_count == 1:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(status_code=404, detail=f"Agent {id} not found")


@router.get(
    "/find/",
    response_description="Get agent id by specified field",
    response_model_by_alias=False
)
async def get_agent_id_by_field(
    email: str = None, phone: str = None, first_name: str = None, last_name: str = None, full_name: str = None
):
    """
    Get the id for a specific agent, looked up by a specified field.
    """
    if first_name and not last_name or last_name and not first_name:
        raise HTTPException(status_code=400, detail="First name and last name must be provided together")
    try:
        agent = await agent_controller.get_agent_by_field(
            email=email, phone=phone, first_name=first_name, last_name=last_name, full_name=full_name
        )
        return {"id": str(agent["_id"])}
    except agent_controller.AgentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
