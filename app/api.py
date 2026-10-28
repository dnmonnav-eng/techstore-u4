from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from cargar_csv import load_fixture
from app.domain import InvalidOrderTransition, InvalidOrderData, OrderItemLimitExceeded

app = FastAPI(title="TechStore U4", version="1.0.0")

# Cargar los pedidos iniciales en memoria
orders = load_fixture()

# Modelos Pydantic para los cuerpos de solicitud que requieren datos
class ShipRequest(BaseModel):
    tracking_number: str

class CancelRequest(BaseModel):
    reason: str

@app.get("/")
def read_root():
    return {"message": "Bienvenido a la API de TechStore - Unidad 4"}

@app.post("/orders/{order_id}/confirm")
def confirm_order(order_id: str):
    order = orders.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    try:
        order.confirm()
    except InvalidOrderTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except (InvalidOrderData, OrderItemLimitExceeded) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"id": order.id, "status": order.status.value, "events": [e.name for e in order.events]}

@app.post("/orders/{order_id}/ship")
def ship_order(order_id: str, body: ShipRequest):
    order = orders.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    try:
        order.ship(body.tracking_number)
    except InvalidOrderTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except (InvalidOrderData, OrderItemLimitExceeded) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"id": order.id, "status": order.status.value, "events": [e.name for e in order.events]}

@app.post("/orders/{order_id}/cancel")
def cancel_order(order_id: str, body: CancelRequest):
    order = orders.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    try:
        order.cancel(body.reason)
    except InvalidOrderTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except (InvalidOrderData, OrderItemLimitExceeded) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"id": order.id, "status": order.status.value, "events": [e.name for e in order.events]}

@app.post("/orders/{order_id}/deliver")
def deliver_order(order_id: str):
    order = orders.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    try:
        order.deliver()
    except InvalidOrderTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except (InvalidOrderData, OrderItemLimitExceeded) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"id": order.id, "status": order.status.value, "events": [e.name for e in order.events]}

@app.post("/orders/{order_id}/return")
def return_order(order_id: str):
    order = orders.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    try:
        order.return_order()
    except InvalidOrderTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except (InvalidOrderData, OrderItemLimitExceeded) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"id": order.id, "status": order.status.value, "events": [e.name for e in order.events]}