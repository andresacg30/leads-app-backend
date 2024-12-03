import ast
import bson

from fastapi import APIRouter, Body, Request, status, HTTPException, Depends, Response

from app.auth.jwt_bearer import get_current_user
from app.controllers import order as order_controller
from app.models.user import UserModel
from app.models.order import OrderModel, UpdateOrderModel, OrderCollection


router = APIRouter(prefix="/api/order", tags=["order"])


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
        return order.to_json()

    except order_controller.OrderNotFoundError:
        raise HTTPException(status_code=404, detail=f"Order {id} not found")



@router.get(
    "",
    response_description="Get all orders",
    response_model_by_alias=False
)
async def list_orders(page: int = 1, limit: int = 10, sort: str = "start_date=DESC" , filter: str = None, user: UserModel = Depends(get_current_user)):
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
            filter["campaign_id"] = {"$in": [bson.ObjectId(campaign) for campaign in user.campaigns]}
        sort = [sort.split('=')[0], 1 if sort.split('=')[1] == "ASC" else -1]
        orders, total = await order_controller.get_all_orders(page=page, limit=limit, sort=sort, filter=filter)
        return {
            "data": list(order.to_json() for order in OrderCollection(data=orders).data),
            "total": total
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
