import ast
import asyncio
from typing import List
import bson

from fastapi import APIRouter, Body, Request, status, HTTPException, Depends, Response

from app.auth.jwt_bearer import get_current_user
from app.controllers import order as order_controller
from app.models.user import UserModel
from app.models.order import OrderModel, UpdateOrderModel, OrderCollection


router = APIRouter(prefix="/api/order", tags=["order"])


@router.put(
    "/{id}",
    response_description="Update an order",
    response_model_by_alias=False
)
async def update_order(
    id: str,
    order_update: UpdateOrderModel,
    user: UserModel = Depends(get_current_user)
):
    """
    Update an order record with validated data.
    """
    try:
        if not user.is_admin():
            if not user.campaigns or order_update.campaign_id not in user.campaigns:
                raise HTTPException(
                    status_code=403,
                    detail="You don't have permission to update this order"
                )
            if user.is_agent() and str(order_update.agent_id) != str(user.agent_id):
                raise HTTPException(
                    status_code=403, 
                    detail="You can only update your own orders"
                )
        updated_order = await order_controller.update_order(id, order_update)
        return {"_id": str(updated_order["_id"])}
    except order_controller.OrderNotFoundError:
        raise HTTPException(status_code=404, detail=f"Order {id} not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get(
    "/{id}",
    response_description="Get a single order",
    response_model_by_alias=False
)
async def show_order(id: str, user: UserModel = Depends(get_current_user)):
    """
    Get the record for a specific order, looked up by `id`.
    """
    try:
        if not user.is_admin():
            if not user.campaigns:
                raise HTTPException(status_code=404, detail="User does not have access to this order")
        order = await order_controller.get_one_order(id)
        return await order.to_json()

    except order_controller.OrderNotFoundError:
        raise HTTPException(status_code=404, detail=f"Order {id} not found")


@router.post(
    "/get-many",
    response_description="Get multiple orders",
    response_model_by_alias=False
)
async def show_orders(ids: List[str] = Body(...), user: UserModel = Depends(get_current_user)):
    """
    Get the record for multiple orders, looked up by `ids`.
    """
    try:
        if not user.is_admin():
            if not user.campaigns:
                raise HTTPException(status_code=404, detail="User does not have access to this order")
        orders = await order_controller.get_many_orders(ids=ids, user=user)
        data = await asyncio.gather(*(order.to_json() for order in OrderCollection(data=orders).data))
        return {"data": data}
    except order_controller.OrderNotFoundError:
        raise HTTPException(status_code=404, detail=f"Order {ids} not found")



@router.get(
    "",
    response_description="Get all orders",
    response_model_by_alias=False
)
async def list_orders(page: int = 1, limit: int = 10, sort: str = "date=DESC" , filter: str = None, user: UserModel = Depends(get_current_user)):
    """
    List all of the order data in the database within the specified page and limit.
    """
    if sort.split('=')[1] not in ["ASC", "DESC"]:
        raise HTTPException(status_code=400, detail="Invalid sort parameter")
    try:
        filter = ast.literal_eval(filter) if filter else None
        if not user.is_admin():
            if not user.campaigns:
                raise HTTPException(status_code=404, detail="User does not have access to this order")
            if not filter.get("campaign_id"):
                filter["campaign_id"] = {"$in": [bson.ObjectId(campaign) for campaign in user.campaigns]}
            else:
                filter["campaign_id"] = {"$in": [bson.ObjectId(campaign) for campaign in filter["campaign_id"]]}
            if "agent_id" in filter:
                if isinstance(filter["agent_id"], str):
                    filter["agent_id"] = {"$in": [bson.ObjectId(filter["agent_id"])]}
                elif isinstance(filter["agent_id"], list):
                    filter["agent_id"] = {"$in": [bson.ObjectId(agent) for agent in filter["agent_id"]]}
            if user.is_agent() or user.is_new_user():
                filter["agent_id"] = bson.ObjectId(user.agent_id)
        else:
            if "campaign_id" in filter:
                filter["campaign_id"] = {"$in": [bson.ObjectId(campaign) for campaign in filter["campaign_id"]]}
            if "agent_id" in filter:
                if isinstance(filter["agent_id"], str):
                    filter["agent_id"] = {"$in": [bson.ObjectId(filter["agent_id"])]}
                elif isinstance(filter["agent_id"], list):
                    filter["agent_id"] = {"$in": [bson.ObjectId(agent) for agent in filter["agent_id"]]}
        sort = [sort.split('=')[0], 1 if sort.split('=')[1] == "ASC" else -1]
        orders, total = await order_controller.get_all_orders(page=page, limit=limit, sort=sort, filter=filter)
        data = await asyncio.gather(*(order.to_json() for order in OrderCollection(data=orders).data))
        return {
            "data": data,
            "total": total
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
