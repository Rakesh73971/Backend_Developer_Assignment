from django.urls import path
from .views import StoreListView, InventoryListView
from apps.orders.views import OrderListView

urlpatterns = [
    path('', StoreListView.as_view(), name='store-list'),
    path('<int:store_id>/inventory/', InventoryListView.as_view(), name='store-inventory'),
    path('<int:store_id>/orders/', OrderListView.as_view(), name='store-orders'),
]
