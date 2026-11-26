from src.payment import PaymentProcessor


def test_charge_adds_tax():
    processor = PaymentProcessor()
    assert processor.charge(100) == 108
