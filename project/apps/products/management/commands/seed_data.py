import random
from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker

from apps.products.models import Category, Product
from apps.stores.models import Store, Inventory
from apps.orders.models import Order, OrderItem

class Command(BaseCommand):
    help = "Seeds dummy data for Categories, Products, Stores, and Inventory."

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data from DB before seeding',
        )

    def handle(self, *args, **options):
        fake = Faker()
        Faker.seed(42)  # For reproducible results
        random.seed(42)

        if options['clear']:
            self.stdout.write("Clearing database...")
            OrderItem.objects.all().delete()
            Order.objects.all().delete()
            Inventory.objects.all().delete()
            Product.objects.all().delete()
            Category.objects.all().delete()
            Store.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Database cleared successfully!"))

        self.stdout.write("Seeding data...")

        # 1. Seed Categories (12 categories)
        category_names = [
            "Electronics", "Clothing & Fashion", "Home & Kitchen", "Books & Stationery",
            "Health & Beauty", "Sports & Outdoors", "Toys & Games", "Automotive",
            "Groceries & Food", "Pet Supplies", "Garden & Outdoor", "Office Products"
        ]

        categories = []
        for name in category_names:
            category, created = Category.objects.get_or_create(name=name)
            categories.append(category)

        self.stdout.write(f"Seeded {len(categories)} categories.")

        # 2. Seed Products (1000 products)
        products_to_create = []
        # Generate some nice looking product titles
        tech_words = ["Smart", "Ultra", "Power", "Eco", "Elite", "Pro", "Flex", "Sync", "Max", "Air"]
        noun_words = ["Watch", "Phone", "Bottle", "Cooker", "Bag", "Vacuum", "Speaker", "Charger", "Heater", "Hub"]

        existing_count = Product.objects.count()
        if existing_count < 1000:
            target_to_seed = 1000 - existing_count
            for i in range(target_to_seed):
                title = f"{random.choice(tech_words)} {random.choice(noun_words)} {fake.word().capitalize()}"
                desc = fake.paragraph(nb_sentences=2)
                price = round(random.uniform(9.99, 899.99), 2)
                category = random.choice(categories)
                products_to_create.append(
                    Product(
                        title=title,
                        description=desc,
                        price=price,
                        category=category
                    )
                )
            Product.objects.bulk_create(products_to_create)
            self.stdout.write(f"Created {len(products_to_create)} new products.")
        else:
            self.stdout.write(f"Database already has {existing_count} products. Skipping product creation.")

        # Fetch all products from DB for inventory mapping
        all_products = list(Product.objects.all())

        # 3. Seed Stores (25 stores)
        stores_to_create = []
        existing_stores = Store.objects.count()
        if existing_stores < 25:
            target_stores = 25 - existing_stores
            for i in range(target_stores):
                name = f"Aforro {fake.company()} Hub"
                loc = f"{fake.street_address()}, {fake.city()}"
                stores_to_create.append(Store(name=name, location=loc))
            Store.objects.bulk_create(stores_to_create)
            self.stdout.write(f"Created {len(stores_to_create)} new stores.")
        else:
            self.stdout.write(f"Database already has {existing_stores} stores. Skipping store creation.")

        all_stores = list(Store.objects.all())

        # 4. Seed Inventory (each store maps to at least 300 products)
        existing_inventory = Inventory.objects.count()
        if existing_inventory > 0:
            self.stdout.write(f"Database already has {existing_inventory} inventory records. Skipping inventory creation.")
        else:
            self.stdout.write("Mapping inventory for each store...")
            inventory_items = []

            with transaction.atomic():
                for store in all_stores:
                    # Randomly pick 350-400 products for this store to stock
                    sample_size = random.randint(320, 380)
                    selected_products = random.sample(all_products, sample_size)
                    
                    for product in selected_products:
                        # Let's seed quantities between 0 and 150 (some out of stock to test edge cases)
                        quantity = random.choice([0] * 5 + list(range(1, 150)))
                        inventory_items.append(
                            Inventory(
                                store=store,
                                product=product,
                                quantity=quantity
                            )
                        )

                # Ignore conflicts in case of duplicate runs
                Inventory.objects.bulk_create(inventory_items, ignore_conflicts=True)

            self.stdout.write(f"Seeded inventory. Total inventory rows created: {len(inventory_items)}.")
        self.stdout.write(self.style.SUCCESS("Database seeding completed successfully!"))
