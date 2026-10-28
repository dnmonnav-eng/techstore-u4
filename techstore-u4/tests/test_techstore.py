"""Pruebas automáticas del núcleo de negocio TechStore (21 pruebas en un solo archivo).

Cada prueba sigue tres partes: 1) PREPARAR datos  2) EJECUTAR la acción  3) COMPROBAR el resultado.
Si una prueba falla, se corrige la implementación (app/), nunca el resultado esperado.

Contenido
  Pruebas 01-10  Las exigidas por la guía (punto 12)
  Pruebas 11-17  Reglas adicionales de dominio y Specifications
  Pruebas 18-21  API REST (códigos HTTP 404, 409 y 422)

Ejecutar:  python -m pytest -q
"""
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app import api
from app.domain import (
    Customer, InvalidOrderData, InvalidOrderTransition, Money, Order, OrderItem,
    OrderItemLimitExceeded, OrderStatus,
)
from app.specifications import (
    ActivePromotionSpec, MinimumAmountSpec, VIPCustomerSpec,
    get_five_percent_spec, get_ten_percent_spec,
)
from cargar_csv import load_fixture

ten = get_ten_percent_spec()
five = get_five_percent_spec()


# =========================================================================
# Ayudas para preparar datos
# =========================================================================
def make_order(oid="T1", qty=1, vip=False, active=True, promo=False, price="100.00"):
    """Pedido en DRAFT con un renglón de 'qty' unidades a 'price' cada una."""
    order = Order(customer=Customer(id="C1", is_vip=vip, active=active),
                  id=oid, has_promotion=promo)
    if qty:
        order.add_item(OrderItem("SKU001", qty, Money(Decimal(price))))
    return order


@pytest.fixture
def client():
    """Cliente HTTP de prueba con datos limpios (los endpoints modifican el estado en memoria)."""
    api.orders.clear()
    api.orders.update(load_fixture())
    return TestClient(api.app)


def state(order_id):
    """Estado y eventos reales de un pedido guardado en la API."""
    o = api.orders[order_id]
    return o.status.value, [e.name for e in o.events]


# =========================================================================
# PRUEBAS EXIGIDAS POR LA GUÍA
# =========================================================================
def test_01_money_negativo():
    # 1) Preparar: un monto negativo
    monto = Decimal("-1")
    # 2) Ejecutar + 3) Comprobar: el constructor lo rechaza
    with pytest.raises(InvalidOrderData):
        Money(monto)


def test_02_pedido_o001_inicia_draft():
    # 1) Preparar: cargar los pedidos del paquete
    orders = load_fixture()
    # 2) Ejecutar: consultar O001
    o001 = orders["O001"]
    # 3) Comprobar: estado inicial, unidades y total
    assert o001.status.value == "DRAFT"
    assert o001.units == 4
    assert o001.total.amount == Decimal("2100.00")


def test_03_21_unidades_lanza_limite_y_no_modifica_el_pedido():
    # 1) Preparar: pedido con 20 unidades (el máximo permitido)
    order = make_order(qty=20)
    # 2) Ejecutar: intentar agregar una unidad más (la 21)
    with pytest.raises(OrderItemLimitExceeded):
        order.add_item(OrderItem("SKU002", 1, Money(Decimal("10"))))
    # 3) Comprobar: el pedido quedó igual que antes
    assert order.units == 20
    assert len(order.items) == 1


def test_04_cliente_inactivo_no_puede_confirmar():
    # 1) Preparar: pedido válido de un cliente inactivo
    order = make_order(active=False)
    # 2) Ejecutar: confirmar
    with pytest.raises(InvalidOrderData):
        order.confirm()
    # 3) Comprobar: sigue en DRAFT y sin eventos
    assert order.status == OrderStatus.DRAFT
    assert order.events == []


def test_05_pedido_vacio_no_puede_confirmarse():
    # 1) Preparar: pedido sin artículos
    order = make_order(qty=0)
    # 2) Ejecutar: confirmar
    with pytest.raises(InvalidOrderData):
        order.confirm()
    # 3) Comprobar: sigue en DRAFT y sin eventos
    assert order.status == OrderStatus.DRAFT
    assert order.events == []


def test_06_descuento_vip_10_por_ciento():
    # 1) Preparar: cliente VIP, 4 unidades, total 2100, sin promoción
    order = make_order(qty=4, vip=True, promo=False, price="525.00")
    # 2) Ejecutar: evaluar la regla del 10 %
    cumple = ten.is_satisfied_by(order)
    # 3) Comprobar: cumple y la Specification no modificó el pedido
    assert order.total.amount == Decimal("2100.00")
    assert cumple is True
    assert order.status == OrderStatus.DRAFT and order.events == []


def test_07_promocion_activa_excluye_los_descuentos():
    # 1) Preparar: pedido que cumpliría todo, pero con promoción activa
    order = make_order(qty=4, vip=True, promo=True, price="2000.00")
    # 2) Ejecutar: evaluar ambas reglas
    aplica_10, aplica_5 = ten.is_satisfied_by(order), five.is_satisfied_by(order)
    # 3) Comprobar: ninguna aplica
    assert aplica_10 is False
    assert aplica_5 is False


def test_08_envio_sin_guia_se_rechaza():
    # 1) Preparar: pedido CONFIRMED
    order = make_order()
    order.confirm()
    # 2) Ejecutar: enviar con guía vacía y con guía en blanco
    for guia in ("", "   "):
        with pytest.raises(InvalidOrderData):
            order.ship(guia)
    # 3) Comprobar: sigue CONFIRMED y no hay evento OrderShipped
    assert order.status == OrderStatus.CONFIRMED
    assert [e.name for e in order.events] == ["OrderConfirmed"]


def test_09_confirmacion_doble_no_agrega_segundo_evento():
    # 1) Preparar: pedido ya confirmado una vez
    order = make_order()
    order.confirm()
    # 2) Ejecutar: confirmarlo otra vez
    with pytest.raises(InvalidOrderTransition):
        order.confirm()
    # 3) Comprobar: sigue CONFIRMED con un solo evento
    assert order.status == OrderStatus.CONFIRMED
    assert [e.name for e in order.events] == ["OrderConfirmed"]


def test_10_cancelacion_desde_shipped_no_esta_permitida():
    # 1) Preparar: pedido enviado
    order = make_order()
    order.confirm()
    order.ship("GUIA-1")
    eventos_antes = len(order.events)
    # 2) Ejecutar: intentar cancelarlo
    with pytest.raises(InvalidOrderTransition):
        order.cancel("Ya no lo quiero")
    # 3) Comprobar: sigue SHIPPED y no se agregó OrderCancelled
    assert order.status == OrderStatus.SHIPPED
    assert len(order.events) == eventos_antes


# =========================================================================
# REGLAS ADICIONALES: dominio y Specifications
# =========================================================================
def test_11_units_suma_cantidades_no_renglones():
    # 1) Preparar: dos renglones, de 3 y 2 unidades
    order = make_order(qty=3)
    order.add_item(OrderItem("SKU002", 2, Money(Decimal("50.00"))))
    # 2) Ejecutar: consultar renglones y unidades
    renglones, unidades = len(order.items), order.units
    # 3) Comprobar: 2 renglones pero 5 unidades
    assert renglones == 2
    assert unidades == 5


def test_12_total_es_suma_de_subtotales():
    # 1) Preparar: 2 × 600.00 + 3 × 300.00
    order = make_order(qty=2, price="600.00")
    order.add_item(OrderItem("SKU002", 3, Money(Decimal("300.00"))))
    # 2) Ejecutar: consultar el total
    total = order.total
    # 3) Comprobar: 1200 + 900 = 2100
    assert total.amount == Decimal("2100.00")


def test_13_monto_exacto_de_500_no_supera_el_umbral():
    # 1) Preparar: dos pedidos VIP de 4 unidades, uno de 500.00 y otro de 500.04
    exacto = make_order(qty=4, vip=True, price="125.00")
    mayor = make_order(qty=4, vip=True, price="125.01")
    # 2) Ejecutar: evaluar la regla del 10 %
    cumple_exacto, cumple_mayor = ten.is_satisfied_by(exacto), ten.is_satisfied_by(mayor)
    # 3) Comprobar: la comparación es estricta (> y no >=)
    assert exacto.total.amount == Decimal("500.00")
    assert cumple_exacto is False
    assert cumple_mayor is True


def test_14_descuento_5_por_ciento_sin_vip():
    # 1) Preparar: cliente NO VIP con total 6000 y sin promoción
    order = make_order(qty=2, vip=False, price="3000.00")
    # 2) Ejecutar: evaluar ambas reglas
    aplica_5, aplica_10 = five.is_satisfied_by(order), ten.is_satisfied_by(order)
    # 3) Comprobar: solo aplica la de 5 %
    assert aplica_5 is True
    assert aplica_10 is False


def test_15_composicion_and_or_not():
    # 1) Preparar: pedido de cliente VIP sin promoción
    order = make_order(qty=4, vip=True, promo=False, price="250.00")
    vip, promo = VIPCustomerSpec(), ActivePromotionSpec()
    # 2) Ejecutar: combinar reglas con & (AND), | (OR) y ~ (NOT)
    and_ok = (vip & ~promo).is_satisfied_by(order)
    and_no = (vip & promo).is_satisfied_by(order)
    or_ok = (vip | promo).is_satisfied_by(order)
    not_ok = (~promo).is_satisfied_by(order)
    # 3) Comprobar: coincide con la tabla de verdad
    assert and_ok is True
    assert and_no is False
    assert or_ok is True
    assert not_ok is True
    assert MinimumAmountSpec(Decimal("500")).is_satisfied_by(order) is True


def test_16_flujo_completo_registra_eventos_en_orden():
    # 1) Preparar: pedido en DRAFT
    order = make_order()
    # 2) Ejecutar: confirmar, enviar y entregar
    order.confirm()
    order.ship("GUIA-123")
    order.deliver()
    # 3) Comprobar: estado final y eventos en orden
    assert order.status == OrderStatus.DELIVERED
    assert [e.name for e in order.events] == ["OrderConfirmed", "OrderShipped", "OrderDelivered"]


def test_17_devolucion_desde_shipped_es_valida():
    # 1) Preparar: pedido enviado
    order = make_order()
    order.confirm()
    order.ship("GUIA-9")
    # 2) Ejecutar: devolverlo
    order.return_order()
    # 3) Comprobar: RETURNED y último evento OrderReturned
    assert order.status == OrderStatus.RETURNED
    assert order.events[-1].name == "OrderReturned"


# =========================================================================
# API REST: códigos HTTP
# =========================================================================
def test_18_api_confirmar_pedido_vacio_devuelve_422(client):
    # 1) Preparar: un pedido sin artículos dentro de la API
    api.orders["VACIO"] = make_order(oid="VACIO", qty=0)
    # 2) Ejecutar: pedir confirmarlo
    r = client.post("/orders/VACIO/confirm")
    # 3) Comprobar: 422 y el pedido no cambió
    assert r.status_code == 422
    assert state("VACIO") == ("DRAFT", [])


def test_19_api_pedido_inexistente_devuelve_404(client):
    # 1) Preparar: un ID que no existe
    order_id = "NO-EXISTE"
    # 2) Ejecutar: pedir confirmarlo
    r = client.post(f"/orders/{order_id}/confirm")
    # 3) Comprobar: 404 y no se creó ningún pedido
    assert r.status_code == 404
    assert order_id not in api.orders


def test_20_api_confirmar_dos_veces_devuelve_409(client):
    # 1) Preparar: pedido válido ya confirmado
    api.orders["T1"] = make_order(oid="T1")
    primero = client.post("/orders/T1/confirm")
    # 2) Ejecutar: confirmarlo por segunda vez
    segundo = client.post("/orders/T1/confirm")
    # 3) Comprobar: 200 la primera vez, 409 la segunda y un solo evento
    assert primero.status_code == 200
    assert segundo.status_code == 409
    assert state("T1") == ("CONFIRMED", ["OrderConfirmed"])


def test_21_api_demo_o013_confirmar_repetir_e_inexistente(client):
    # 1) Preparar: O013 viene en DRAFT desde los CSV
    # 2) Ejecutar: confirmar, repetir y confirmar uno inexistente
    primero = client.post("/orders/O013/confirm")
    repetido = client.post("/orders/O013/confirm")
    inexistente = client.post("/orders/O999/confirm")
    # 3) Comprobar
    assert primero.status_code == 200 and primero.json()["status"] == "CONFIRMED"
    assert repetido.status_code == 409
    assert inexistente.status_code == 404
    assert state("O013") == ("CONFIRMED", ["OrderConfirmed"])
