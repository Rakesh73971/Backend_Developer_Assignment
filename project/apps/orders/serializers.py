from rest_framework import serializers
from .models import Order, OrderItem

class OrderItemSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source='product.title', read_only=True)
    price = serializers.DecimalField(source='product.price', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_title', 'price', 'quantity_requested']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'store', 'status', 'created_at', 'items', 'total_items']

class OrderItemRequestSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(help_text="ID of the product to order")
    quantity_requested = serializers.IntegerField(help_text="Quantity of the product requested")

class OrderCreateRequestSerializer(serializers.Serializer):
    store_id = serializers.IntegerField(help_text="ID of the store where the order is placed")
    items = OrderItemRequestSerializer(many=True, help_text="List of items in the order")

