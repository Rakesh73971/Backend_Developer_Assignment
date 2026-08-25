import logging
from celery import shared_task
from django.db.models import Sum

logger = logging.getLogger(__name__)

@shared_task
def send_order_confirmation(order_id):
    """
    Asynchronous Celery task that simulates sending an order confirmation.
    In a real-world scenario, this would send an email, SMS, or webhook notification.
    """
    from apps.orders.models import Order
    try:
        order = Order.objects.get(id=order_id)
        if order.status != 'CONFIRMED':
            logger.warning(f"Attempted to send order confirmation for Order #{order_id} which is {order.status}.")
            return f"Skipped: Order #{order_id} is not CONFIRMED"

        logger.info(f"--- ORDER CONFIRMATION SENT ---")
        logger.info(f"Order ID: {order.id}")
        logger.info(f"Store: {order.store.name} (ID: {order.store.id})")
        logger.info(f"Created At: {order.created_at}")
        
        items_summary = []
        for item in order.items.select_related('product'):
            items_summary.append(f"{item.product.title} (x{item.quantity_requested})")
        logger.info(f"Items: {', '.join(items_summary)}")
        logger.info(f"--------------------------------")

        return f"Success: Confirmation sent for Order #{order.id}"
    except Order.DoesNotExist:
        logger.error(f"Failed to send confirmation: Order #{order_id} does not exist.")
        return f"Error: Order #{order_id} not found"

@shared_task
def generate_daily_inventory_summary():
    """
    Celery Beat task running daily to generate and log inventory summary reports.
    Computes total stores, total items stocked, and average stock per store.
    """
    from apps.stores.models import Store, Inventory
    
    total_stores = Store.objects.count()
    total_stock = Inventory.objects.aggregate(total_qty=Sum('quantity'))['total_qty'] or 0
    total_distinct_products = Inventory.objects.values('product_id').distinct().count()

    summary_msg = (
        f"=== DAILY INVENTORY SUMMARY REPORT ===\n"
        f"Active Stores: {total_stores}\n"
        f"Total Mapped Products: {total_distinct_products}\n"
        f"Total Stocked Units across all stores: {total_stock}\n"
        f"Average Stock per store: {total_stock / max(total_stores, 1):.2f}\n"
        f"====================================="
    )
    logger.info(summary_msg)
    print(summary_msg)
    return "Daily inventory summary completed successfully"
