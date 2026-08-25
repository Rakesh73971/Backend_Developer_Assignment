from rest_framework import serializers
from .models import Category, Product

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    # inventory_quantity will be annotated dynamically when store_id is provided in searches
    inventory_quantity = serializers.IntegerField(required=False, read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'title', 'description', 'price', 'category', 'category_name', 'inventory_quantity', 'created_at']
