from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

MAX_UNITS_PER_ORDER = 20
CURRENCY = "MXN"


# --------------------------------------------------------------------------
# Excepciones de dominio
# --------------------------------------------------------------------------
class DomainException(Exception):
    """Una regla de negocio fue violada (no es una falla técnica)."""


class OrderException(DomainException):
    """Violación de reglas propias del pedido."""


class InvalidOrderData(OrderException):
    """Datos inválidos: monto negativo, pedido vacío, cliente inactivo, etc."""


class InvalidOrderTransition(OrderException):
    """Operación no permitida desde el estado actual del pedido."""


class OrderItemLimitExceeded(OrderException):
    """El pedido superaría el máximo de 20 unidades."""


# --------------------------------------------------------------------------
# Value Objects
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Money:
    """Importe inmutable. Se compara por valor y nunca puede ser negativo."""

    amount: Decimal
    currency: str = CURRENCY

    def __post_init__(self):
        amount = self.amount
        # float introduce errores binarios (0.1 + 0.2 != 0.3): se rechaza.
        if isinstance(amount, (bool, float)):
            raise InvalidOrderData("Monto inválido: use Decimal, no float")
        if isinstance(amount, int):
            object.__setattr__(self, "amount", Decimal(amount))
            amount = self.amount
        if not isinstance(amount, Decimal):
            raise InvalidOrderData("Monto inválido")
        if not amount.is_finite() or amount < 0:
            raise InvalidOrderData("Monto inválido")
        if not isinstance(self.currency, str) or not self.currency.strip():
            raise InvalidOrderData("Moneda inválida")

    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise InvalidOrderData("Monedas distintas")
        return Money(self.amount + other.amount, self.currency)

    def multiply(self, quantity: int) -> "Money":
        return Money(self.amount * quantity, self.currency)

    def __str__(self) -> str:
        return f"{self.amount:.2f} {self.currency}"


@dataclass(frozen=True)
class OrderItem:
    """Renglón del pedido: producto, cantidad y precio unitario."""

    sku: str
    quantity: int
    unit_price: Money

    def __post_init__(self):
        if not isinstance(self.sku, str) or not self.sku.strip():
            raise InvalidOrderData("Artículo inválido: SKU vacío")
        if (not isinstance(self.quantity, int) or isinstance(self.quantity, bool)
                or self.quantity <= 0):
            raise InvalidOrderData("Artículo inválido: cantidad debe ser > 0")
        if not isinstance(self.unit_price, Money):
            raise InvalidOrderData("Artículo inválido: precio no es Money")

    @property
    def subtotal(self) -> Money:
        # Se calcula; nunca se captura a mano (evita discrepancias).
        return self.unit_price.multiply(self.quantity)


# --------------------------------------------------------------------------
# Entidades
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Customer:
    id: str
    is_vip: bool = False
    active: bool = True

    def __post_init__(self):
        if not isinstance(self.id, str) or not self.id.strip():
            raise InvalidOrderData("Cliente inválido: id vacío")


class OrderStatus(str, Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    RETURNED = "RETURNED"


@dataclass(frozen=True)
class DomainEvent:
    """Hecho ya ocurrido (nombre en pasado). Inmutable y con marca de tiempo."""

    name: str
    order_id: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    detail: str = ""  # guía de envío o motivo de cancelación, si aplica


_PAST = {
    OrderStatus.CONFIRMED: "confirmado",
    OrderStatus.SHIPPED: "enviado",
    OrderStatus.CANCELLED: "cancelado",
    OrderStatus.DELIVERED: "entregado",
    OrderStatus.RETURNED: "devuelto",
}


@dataclass(eq=False)  # la igualdad de una entidad la da su identidad, no sus campos
class Order:
    """Aggregate Root. Es la única vía para modificar items, status y events."""

    customer: Customer
    id: str
    has_promotion: bool = False
    status: OrderStatus = OrderStatus.DRAFT
    items: list = field(default_factory=list)
    events: list = field(default_factory=list)
    tracking_number: Optional[str] = None
    cancel_reason: Optional[str] = None

    # -- identidad ---------------------------------------------------------
    def __eq__(self, other):
        return isinstance(other, Order) and self.id == other.id

    def __hash__(self):
        return hash(self.id)

    # -- consultas ---------------------------------------------------------
    @property
    def units(self) -> int:
        """SUMA de cantidades (no el número de renglones)."""
        return sum(item.quantity for item in self.items)

    @property
    def total(self) -> Money:
        amount = sum((x.subtotal.amount for x in self.items), Decimal("0"))
        return Money(amount)

    # -- comandos ----------------------------------------------------------
    def add_item(self, item: OrderItem) -> None:
        if self.status != OrderStatus.DRAFT:
            raise InvalidOrderTransition(
                f"El pedido {self.id} está en estado {self.status.value}; "
                "solo un pedido DRAFT admite artículos"
            )
        if not isinstance(item, OrderItem):
            raise InvalidOrderData("Artículo inválido")
        if self.units + item.quantity > MAX_UNITS_PER_ORDER:
            raise OrderItemLimitExceeded(
                f"El pedido {self.id} no puede tener más de {MAX_UNITS_PER_ORDER} unidades "
                f"(tiene {self.units} y se intentan agregar {item.quantity})"
            )
        if item.unit_price.currency != CURRENCY:
            raise InvalidOrderData("Solo se admite la moneda MXN")
        self.items.append(item)

    def confirm(self) -> None:
        self._require(OrderStatus.DRAFT, "confirmar", OrderStatus.CONFIRMED)
        if not self.items:
            raise InvalidOrderData(f"El pedido {self.id} no tiene artículos; no se puede confirmar vacío")
        if not self.customer.active:
            raise InvalidOrderData(
                f"El cliente {self.customer.id} está inactivo; no puede confirmar el pedido {self.id}"
            )
        self._move_to(OrderStatus.CONFIRMED, "OrderConfirmed")

    def ship(self, tracking_number: str) -> None:
        self._require(OrderStatus.CONFIRMED, "enviar", OrderStatus.SHIPPED)
        if not isinstance(tracking_number, str) or not tracking_number.strip():
            raise InvalidOrderData("Se requiere un número de guía válido para enviar el pedido")
        self.tracking_number = tracking_number.strip()
        self._move_to(OrderStatus.SHIPPED, "OrderShipped", self.tracking_number)

    def cancel(self, reason: str) -> None:
        self._require(OrderStatus.CONFIRMED, "cancelar", OrderStatus.CANCELLED)
        if not isinstance(reason, str) or not reason.strip():
            raise InvalidOrderData("Se requiere un motivo para cancelar el pedido")
        self.cancel_reason = reason.strip()
        self._move_to(OrderStatus.CANCELLED, "OrderCancelled", self.cancel_reason)

    def deliver(self) -> None:
        self._require(OrderStatus.SHIPPED, "entregar", OrderStatus.DELIVERED)
        self._move_to(OrderStatus.DELIVERED, "OrderDelivered")

    def return_order(self) -> None:
        self._require(OrderStatus.SHIPPED, "devolver", OrderStatus.RETURNED)
        self._move_to(OrderStatus.RETURNED, "OrderReturned")

    def pull_events(self) -> list:
        """Entrega los eventos acumulados y los limpia (los publicaría la infraestructura)."""
        pending, self.events = self.events, []
        return pending

    # -- helpers privados --------------------------------------------------
    def _require(self, expected: OrderStatus, action: str, target: OrderStatus) -> None:
        """Valida el estado actual con mensajes que el usuario de la API entiende."""
        if self.status == target:
            # Repetir una operación ya realizada (ej. confirmar dos veces).
            raise InvalidOrderTransition(
                f"El pedido {self.id} ya fue {_PAST[target]} (estado actual: "
                f"{self.status.value}); no se puede {action} de nuevo"
            )
        if self.status != expected:
            raise InvalidOrderTransition(
                f"No se puede {action} el pedido {self.id}: está en estado "
                f"{self.status.value} y solo se puede {action} desde {expected.value}"
            )

    def _move_to(self, new_status: OrderStatus, event_name: str, detail: str = "") -> None:
        # Se llama SOLO cuando todas las validaciones ya pasaron:
        # primero cambia el estado y al final se registra el evento.
        self.status = new_status
        self.events.append(DomainEvent(event_name, self.id, detail=detail))
