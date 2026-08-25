from unittest.mock import patch
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.products.models import Product, Category
from apps.stores.models import Store, Inventory
from apps.orders.models import Order, OrderItem

@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    CACHES={
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
    }
)
class OrderCreationTests(APITestCase):

    def setUp(self):
        # Create Category and Products
        self.category = Category.objects.create(name="Tech")
        self.product1 = Product.objects.create(title="Laptop", price=500.00, category=self.category)
        self.product2 = Product.objects.create(title="Mouse", price=25.00, category=self.category)

        # Create Store
        self.store = Store.objects.create(name="Aforro Store Alpha", location="Sector 5, Noida")

        # Set Store Inventory
        self.inv1 = Inventory.objects.create(store=self.store, product=self.product1, quantity=10)
        self.inv2 = Inventory.objects.create(store=self.store, product=self.product2, quantity=5)

        self.url = reverse('order-create')

    def test_order_creation_success(self):
        """
        Tests order creation when all items are in stock.
        Should result in: CONFIRMED status, deducted quantities.
        """
        payload = {
            "store_id": self.store.id,
            "items": [
                {"product_id": self.product1.id, "quantity_requested": 3},
                {"product_id": self.product2.id, "quantity_requested": 5}
            ]
        }
        
        response = self.client.post(self.url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'CONFIRMED')
        self.assertEqual(response.data['total_items'], 8)

        # Validate Stock Deduction
        self.inv1.refresh_from_db()
        self.inv2.refresh_from_db()
        self.assertEqual(self.inv1.quantity, 7)  # 10 - 3
        self.assertEqual(self.inv2.quantity, 0)  # 5 - 5

        # Validate Order and Items exists in DB
        order = Order.objects.get(id=response.data['id'])
        self.assertEqual(order.status, 'CONFIRMED')
        self.assertEqual(order.items.count(), 2)

    def test_order_creation_insufficient_stock_rejection(self):
        """
        Tests order creation when at least one item has insufficient stock.
        Should result in: REJECTED status, zero stock deduction.
        """
        payload = {
            "store_id": self.store.id,
            "items": [
                {"product_id": self.product1.id, "quantity_requested": 2},
                {"product_id": self.product2.id, "quantity_requested": 10} # Only 5 available
            ]
        }
        
        response = self.client.post(self.url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'REJECTED')
        self.assertIn('errors', response.data)

        # Validate Zero Stock Deduction
        self.inv1.refresh_from_db()
        self.inv2.refresh_from_db()
        self.assertEqual(self.inv1.quantity, 10)  # Unchanged
        self.assertEqual(self.inv2.quantity, 5)   # Unchanged

        # Order Items should still exist for audit purposes
        order = Order.objects.get(id=response.data['id'])
        self.assertEqual(order.status, 'REJECTED')
        self.assertEqual(order.items.count(), 2)

    @patch('apps.orders.views.Inventory.objects.bulk_update')
    def test_order_creation_atomic_rollback(self, mock_bulk_update):
        """
        Tests database atomicity. If an unexpected exception occurs during inventory
        deduction, all changes (like Order creation and OrderItem insertion) must be rolled back.
        """
        mock_bulk_update.side_effect = Exception("Simulated database connection failure during update")
        
        payload = {
            "store_id": self.store.id,
            "items": [
                {"product_id": self.product1.id, "quantity_requested": 3},
                {"product_id": self.product2.id, "quantity_requested": 1}
            ]
        }

        # The exception raised inside with transaction.atomic() propagates out of the view
        with self.assertRaises(Exception):
            self.client.post(self.url, payload, format='json')

        # Validate that the Order and OrderItems were rolled back and do not exist in the DB
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(OrderItem.objects.count(), 0)

        # Validate that no stock was deducted
        self.inv1.refresh_from_db()
        self.inv2.refresh_from_db()
        self.assertEqual(self.inv1.quantity, 10)
        self.assertEqual(self.inv2.quantity, 5)

    def test_order_creation_rejects_unknown_product_id(self):
        """
        Unknown products are invalid input and should not create an order or raise 500.
        """
        payload = {
            "store_id": self.store.id,
            "items": [
                {"product_id": 999999, "quantity_requested": 1}
            ]
        }

        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 0)
        self.assertIn('errors', response.data)

    def test_duplicate_product_lines_are_validated_as_total_quantity(self):
        """
        Repeated product lines must be checked against stock as one combined request.
        """
        payload = {
            "store_id": self.store.id,
            "items": [
                {"product_id": self.product1.id, "quantity_requested": 6},
                {"product_id": self.product1.id, "quantity_requested": 5}
            ]
        }

        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'REJECTED')

        self.inv1.refresh_from_db()
        self.assertEqual(self.inv1.quantity, 10)
