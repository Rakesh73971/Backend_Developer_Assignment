from collections import defaultdict

from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Order, OrderItem
from drf_spectacular.utils import extend_schema
from .serializers import OrderSerializer, OrderCreateRequestSerializer
from apps.stores.models import Store, Inventory
from apps.products.models import Product
from .tasks import send_order_confirmation

@extend_schema(
    request=OrderCreateRequestSerializer,
    responses={
        201: OrderSerializer,
        200: OrderSerializer,
        400: dict
    },
    description="Creates a new store order after locking and validating inventory stock levels."
)
class OrderCreateView(APIView):
    """
    Endpoint: POST /orders/
    Creates an order with items for a specific store.
    Uses transaction.atomic() and select_for_update() to prevent concurrent stock race conditions.
    """
    def post(self, request, *args, **kwargs):
        store_id = request.data.get('store_id')
        items_data = request.data.get('items', [])

        if not store_id or not items_data:
            return Response(
                {"error": "Both store_id and a non-empty list of items are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            store = Store.objects.get(id=store_id)
        except Store.DoesNotExist:
            return Response(
                {"error": f"Store with ID {store_id} does not exist."},
                status=status.HTTP_400_BAD_REQUEST
            )

        requested_quantities = defaultdict(int)
        validation_errors = []

        for item in items_data:
            product_id = item.get('product_id')
            quantity_requested = item.get('quantity_requested')

            try:
                product_id = int(product_id)
                quantity_requested = int(quantity_requested)
            except (TypeError, ValueError):
                validation_errors.append("Each item must contain a valid product_id and quantity_requested.")
                continue

            if quantity_requested <= 0:
                validation_errors.append(f"Quantity requested for product {product_id} must be greater than 0.")
                continue

            requested_quantities[product_id] += quantity_requested

        if validation_errors or not requested_quantities:
            return Response(
                {"errors": validation_errors or ["At least one valid order item is required."]},
                status=status.HTTP_400_BAD_REQUEST
            )

        product_ids = list(requested_quantities.keys())
        product_map = Product.objects.in_bulk(product_ids)
        missing_product_ids = sorted(set(product_ids) - set(product_map.keys()))
        if missing_product_ids:
            return Response(
                {"errors": [f"Products do not exist: {missing_product_ids}."]},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Wrap in atomic transaction for consistent inventory deduction and order state transitions
        with transaction.atomic():
            # Lock the inventory rows for the store and the specified products to prevent race conditions
            inventories = Inventory.objects.filter(
                store=store,
                product_id__in=product_ids
            ).select_for_update()

            inventory_map = {inv.product_id: inv for inv in inventories}
            
            sufficient_stock = True
            stock_errors = []

            # Validate aggregated quantities against locked inventory stock
            for prod_id, qty_requested in requested_quantities.items():
                inv = inventory_map.get(prod_id)
                if not inv:
                    stock_errors.append(f"Product {prod_id} is not stocked at this store.")
                    sufficient_stock = False
                elif inv.quantity < qty_requested:
                    stock_errors.append(
                        f"Insufficient stock for product {prod_id}. Requested: {qty_requested}, Available: {inv.quantity}."
                    )
                    sufficient_stock = False

            # Create Order record (either CONFIRMED or REJECTED)
            order_status = 'CONFIRMED' if sufficient_stock else 'REJECTED'
            order = Order.objects.create(store=store, status=order_status)

            # Create OrderItems for auditing and tracking
            order_items = []
            for prod_id, qty_requested in requested_quantities.items():
                order_items.append(
                    OrderItem(
                        order=order,
                        product=product_map[prod_id],
                        quantity_requested=qty_requested
                    )
                )
            OrderItem.objects.bulk_create(order_items)

            # If stock was sufficient, deduct and commit; trigger confirmation notification
            if sufficient_stock:
                inventories_to_update = []
                for prod_id, qty_requested in requested_quantities.items():
                    inv = inventory_map[prod_id]
                    inv.quantity -= qty_requested
                    inventories_to_update.append(inv)
                Inventory.objects.bulk_update(inventories_to_update, ['quantity'])
                
                # Trigger Celery Async Task
                transaction.on_commit(lambda: send_order_confirmation.delay(order.id))
            
            # Serialize the response
            serializer = OrderSerializer(order)
            
            # Annotate manually for response consistency
            response_data = serializer.data
            response_data['total_items'] = sum(requested_quantities.values())
            
            if not sufficient_stock:
                response_data['errors'] = stock_errors
                return Response(response_data, status=status.HTTP_200_OK)

            return Response(response_data, status=status.HTTP_201_CREATED)

class OrderListView(generics.ListAPIView):
    """
    Endpoint: GET /stores/<store_id>/orders/
    Lists all orders for a store, including item counts. Sorted newest first.
    Optimized to eliminate N+1 queries.
    """
    serializer_class = OrderSerializer

    def get_queryset(self):
        store_id = self.kwargs['store_id']
        # We prefetch order items and annotate total items in a single query
        return Order.objects.filter(store=store_id).annotate(
            total_items=Coalesce(Sum('items__quantity_requested'), 0)
        ).prefetch_related(
            'items',
            'items__product'
        ).order_by('-created_at')
