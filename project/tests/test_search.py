from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.products.models import Product, Category
from apps.stores.models import Store, Inventory

@override_settings(
    CACHES={
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
    }
)
class ProductSearchAndSuggestTests(APITestCase):

    def setUp(self):
        # Create Categories
        self.cat_tech = Category.objects.create(name="Tech")
        self.cat_books = Category.objects.create(name="Books")

        # Create Products
        self.prod1 = Product.objects.create(title="Super Phone", description="High end smartphone", price=699.99, category=self.cat_tech)
        self.prod2 = Product.objects.create(title="Smart Watch", description="Interactive wearable device", price=199.99, category=self.cat_tech)
        self.prod3 = Product.objects.create(title="Learn Django", description="A book about Python web development", price=45.00, category=self.cat_books)
        self.prod4 = Product.objects.create(title="Phone Cover", description="Silicone case protecting phone edges", price=15.00, category=self.cat_tech)
        self.prod5 = Product.objects.create(title="Django Pro Hacks", description="Mastering Django internals", price=55.00, category=self.cat_books)

        # Create Store and Stock
        self.store = Store.objects.create(name="Main Tech Hub", location="New Delhi")
        # stock: Phone is out of stock, Watch is in stock, Learn Django is not stocked at all
        Inventory.objects.create(store=self.store, product=self.prod1, quantity=0)
        Inventory.objects.create(store=self.store, product=self.prod2, quantity=10)
        Inventory.objects.create(store=self.store, product=self.prod4, quantity=25)

        self.search_url = reverse('product-search')
        self.suggest_url = reverse('autocomplete')

    def test_product_search_keyword(self):
        """
        Tests keyword queries matching title, description, and category.
        """
        # Match by category name 'Books'
        response = self.client.get(self.search_url, {"q": "Books"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return 'Learn Django' and 'Django Pro Hacks' since category name matches 'Books'
        titles = [p['title'] for p in response.data['results']]
        self.assertIn("Learn Django", titles)
        self.assertIn("Django Pro Hacks", titles)

        # Match by description text
        response = self.client.get(self.search_url, {"q": "wearable"})
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], "Smart Watch")

    def test_product_search_filters(self):
        """
        Tests category, price range, and store constraints.
        """
        # Category Filter
        response = self.client.get(self.search_url, {"category": "Tech"})
        self.assertEqual(len(response.data['results']), 3) # Phone, Watch, Phone Cover

        # Price Range Filter
        response = self.client.get(self.search_url, {"min_price": "50.00", "max_price": "200.00"})
        titles = [p['title'] for p in response.data['results']]
        self.assertIn("Smart Watch", titles)
        self.assertIn("Django Pro Hacks", titles)
        self.assertNotIn("Super Phone", titles)

        # Store Filter (only return products stocked at store)
        response = self.client.get(self.search_url, {"store_id": self.store.id})
        self.assertEqual(len(response.data['results']), 3) # Phone, Watch, Cover (Not books)
        
        # Store Filter + in_stock Filter (only quantity > 0)
        response = self.client.get(self.search_url, {"store_id": self.store.id, "in_stock": "true"})
        self.assertEqual(len(response.data['results']), 2) # Watch and Cover (Phone is quantity=0)
        titles = [p['title'] for p in response.data['results']]
        self.assertNotIn("Super Phone", titles)

    def test_autocomplete_validation(self):
        """
        Autocomplete requires at least 3 characters. Less should return HTTP 400.
        """
        response = self.client.get(self.suggest_url, {"q": "Ph"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], "Minimum 3 characters required for suggestions.")

    def test_autocomplete_prefix_sorting(self):
        """
        Prefix matches (starts with keyword) must be sorted before contains matches.
        """
        # Search for 'Phone'
        # 'Phone Cover' (starts with Phone) should rank before 'Super Phone' (contains Phone)
        response = self.client.get(self.suggest_url, {"q": "Phone"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        suggestions = response.data
        self.assertEqual(len(suggestions), 2)
        # Verify order
        self.assertEqual(suggestions[0], "Phone Cover")
        self.assertEqual(suggestions[1], "Super Phone")
