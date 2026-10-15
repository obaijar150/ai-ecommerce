"""
Test factories for the orders app using factory_boy.
"""

from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from apps.accounts.tests.factories import UserFactory
from apps.catalog.tests.factories import ProductFactory
from apps.orders.models import CartItem, Order, OrderItem, Payment


class AddressFactory(DjangoModelFactory):
    """Factory for creating shipping addresses."""

    class Meta:
        model = "accounts.Address"

    user = factory.SubFactory(UserFactory)
    label = "Home"
    street = "123 Test Street"
    city = "Testville"
    state = "TS"
    postal_code = "12345"
    country = "United States"
    is_default = True


class CartItemFactory(DjangoModelFactory):
    """Factory for creating cart items (defaults to a user cart)."""

    class Meta:
        model = CartItem

    user = factory.SubFactory(UserFactory)
    product = factory.SubFactory(ProductFactory)
    quantity = 1


class OrderFactory(DjangoModelFactory):
    """Factory for creating orders."""

    class Meta:
        model = Order

    user = factory.SubFactory(UserFactory)
    status = Order.Status.PENDING
    subtotal = Decimal("20.00")
    tax = Decimal("1.60")
    shipping_cost = Decimal("5.99")
    total = Decimal("27.59")
    payment_method = Order.PaymentMethod.MOCK_CARD


class OrderItemFactory(DjangoModelFactory):
    """Factory for creating order line items."""

    class Meta:
        model = OrderItem

    order = factory.SubFactory(OrderFactory)
    product = factory.SubFactory(ProductFactory)
    product_name = factory.LazyAttribute(lambda o: o.product.name)
    product_sku = factory.LazyAttribute(lambda o: o.product.sku)
    quantity = 2
    unit_price = Decimal("10.00")
    total_price = Decimal("20.00")


class PaymentFactory(DjangoModelFactory):
    """Factory for creating payment records."""

    class Meta:
        model = Payment

    order = factory.SubFactory(OrderFactory)
    provider = "mock"
    amount = Decimal("27.59")
    status = Payment.Status.PENDING
