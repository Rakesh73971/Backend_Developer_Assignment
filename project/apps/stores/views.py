from rest_framework import generics
from rest_framework.response import Response
from .models import Inventory, Store
from .serializers import InventorySerializer, StoreSerializer

class StoreListView(generics.ListCreateAPIView):
    queryset = Store.objects.all().order_by('name')
    serializer_class = StoreSerializer
    pagination_class = None

class InventoryListView(generics.ListAPIView):
    serializer_class = InventorySerializer
    pagination_class = None

    def get_queryset(self):
        store_id = self.kwargs['store_id']
        # select_related avoids N+1 queries by fetching product and category in the same JOIN query
        return Inventory.objects.filter(store_id=store_id).select_related(
            'product',
            'product__category'
        ).order_by('product__title')
