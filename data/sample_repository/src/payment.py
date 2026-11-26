"""Payment service demo module. DEMO DATA."""

from src.billing import calculate_tax


class PaymentProcessor:
    def charge(self, amount: float) -> float:
        tax = calculate_tax(amount)
        return amount + tax
