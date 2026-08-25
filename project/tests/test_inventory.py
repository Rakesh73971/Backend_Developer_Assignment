from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.products.models import Product, Category
from apps.stores.models import Store, Inventory

@override_settings(TESTING_WITHOUT_REDIS=True)
class InventoryListingTests(APITestCase):

    def setUp(self):
        # Create Category
        self.category = Category.objects.create(name="Groceries")
        
        # Create products in non-alphabetical title order
        self.product_c = Product.objects.create(title="Cherry", price=1.50, category=self.category)
        self.product_a = Product.objects.create(title="Apple", price=0.99, category=self.category)
        self.product_b = Product.objects.create(title="Banana", price=1.20, category=self.category)

        # Create Store
        self.store = Store.objects.create(name="Aforro Noida Mart", location="Sector 18")

        # Map to Store Inventory
        Inventory.objects.create(store=self.store, product=self.product_c, quantity=10)
        Inventory.objects.create(store=self.store, product=self.product_a, quantity=100)
        Inventory.objects.create(store=self.store, product=self.product_b, quantity=50)

        # URL path
        self.url = reverse('store-inventory', kwargs={'store_id': self.store.id})

    def test_inventory_list_format_and_sorting(self):
        """
        Tests GET /stores/<store_id>/inventory/ returns status 200,
        the objects are sorted alphabetically by product title (Apple -> Banana -> Cherry),
        and contains the required product detail properties.
        """
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check quantity of elements returned
        self.assertEqual(len(response.data), 3)

        # Verify alphabetical sorting by product title
        titles = [item['product_title'] for item in response.data]
        self.assertEqual(titles, ["Apple", "Banana", "Cherry"])

        # Check properties of the first element (Apple)
        first_item = response.data[0]
        self.assertEqual(first_item['product_title'], "Apple")
        self.assertEqual(first_item['category_name'], "Groceries")
        self.assertEqual(float(first_item['price']), 0.99)
        self.assertEqual(first_item['quantity'], 100)
