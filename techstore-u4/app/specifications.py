from decimal import Decimal

class Specification:
    def is_satisfied_by(self, order) -> bool:
        raise NotImplementedError
    
    def __and__(self, other):
        return AndSpec(self, other)
    
    def __or__(self, other):
        return OrSpec(self, other)
    
    def __invert__(self):
        return NotSpec(self)

class AndSpec(Specification):
    def __init__(self, left, right):
        self.left, self.right = left, right
    def is_satisfied_by(self, order):
        return (self.left.is_satisfied_by(order) and self.right.is_satisfied_by(order))

class OrSpec(Specification):
    def __init__(self, left, right):
        self.left, self.right = left, right
    def is_satisfied_by(self, order):
        return (self.left.is_satisfied_by(order) or self.right.is_satisfied_by(order))

class NotSpec(Specification):
    def __init__(self, spec):
        self.spec = spec
    def is_satisfied_by(self, order):
        return not self.spec.is_satisfied_by(order)

class MinimumAmountSpec(Specification):
    def __init__(self, min_amount: Decimal):
        self.min_amount = min_amount
    def is_satisfied_by(self, order):
        return order.total.amount > self.min_amount

class VIPCustomerSpec(Specification):
    def is_satisfied_by(self, order):
        return order.customer.is_vip

class MinimumUnitsSpec(Specification):
    def __init__(self, min_units: int):
        self.min_units = min_units
    def is_satisfied_by(self, order):
        return order.units >= self.min_units

class ActivePromotionSpec(Specification):
    def is_satisfied_by(self, order):
        return order.has_promotion

def get_ten_percent_spec():
    return (
        MinimumAmountSpec(Decimal("500"))
        & VIPCustomerSpec()
        & MinimumUnitsSpec(4)
        & ~ActivePromotionSpec()
    )

def get_five_percent_spec():
    return (
        MinimumAmountSpec(Decimal("5000"))
        & ~ActivePromotionSpec()
    )