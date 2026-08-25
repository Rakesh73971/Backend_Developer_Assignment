import logging
from django.db.models import Q, OuterRef, Subquery, IntegerField, Case, When, Value, BooleanField
from django.db.models.functions import Coalesce
from django.core.cache import cache
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from drf_spectacular.utils import extend_schema, OpenApiParameter

from apps.products.models import Product, Category
from apps.products.serializers import ProductSerializer, CategorySerializer
from apps.stores.models import Inventory

logger = logging.getLogger(__name__)

class SuggestRateThrottle(SimpleRateThrottle):
    """
    Custom DRF rate limiter for autocomplete suggestions.
    Throttles request at 20 requests per minute per user/IP.
    """
    scope = 'suggest_rate'

    def get_cache_key(self, request, view):
        # Identify requester by IP address
        ident = self.get_ident(request)
        return self.cache_format % {'scope': self.scope, 'ident': ident}

@extend_schema(
    parameters=[
        OpenApiParameter(name='q', type=str, description="Search keyword in product title, description, or category name"),
        OpenApiParameter(name='category', type=str, description="Category ID or Category Name filter"),
        OpenApiParameter(name='min_price', type=float, description="Minimum price filter"),
        OpenApiParameter(name='max_price', type=float, description="Maximum price filter"),
        OpenApiParameter(name='store_id', type=int, description="Store ID filter (annotates store-specific stock quantity)"),
        OpenApiParameter(name='in_stock', type=bool, description="Set to true to only show in-stock products"),
        OpenApiParameter(name='sort', type=str, enum=['price', '-price', 'newest', 'relevance'], description="Sorting criteria (default: relevance)"),
    ],
    description="Searches and filters products by keywords, category, price ranges, and store stock level."
)
class ProductSearchView(generics.ListAPIView):
    """
    Endpoint: GET /api/search/products/
    Full-text / multi-field search and filtering API for Products.
    """
    serializer_class = ProductSerializer

    def get_queryset(self):
        queryset = Product.objects.all().select_related('category')

        # 1. Filter by keyword (title, description, category name)
        q = self.request.query_params.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(title__icontains=q) |
                Q(description__icontains=q) |
                Q(category__name__icontains=q)
            )

        # 2. Filter by category (by ID or name)
        category_param = self.request.query_params.get('category')
        if category_param:
            if category_param.isdigit():
                queryset = queryset.filter(category_id=category_param)
            else:
                queryset = queryset.filter(category__name__iexact=category_param)

        # 3. Filter by price range
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)

        # 4. Filter by store_id (products containing inventory mapping at this store)
        store_id = self.request.query_params.get('store_id')
        in_stock = self.request.query_params.get('in_stock', '').lower() == 'true'

        if store_id:
            # Must explicitly filter products stocked at that store
            queryset = queryset.filter(inventories__store_id=store_id)
            if in_stock:
                queryset = queryset.filter(inventories__quantity__gt=0)
        elif in_stock:
            # If in_stock=True without store_id, filter products with stock > 0 in any store
            queryset = queryset.filter(inventories__quantity__gt=0).distinct()

        # 5. Annotate store inventory quantity if store_id is provided
        if store_id:
            inventory_subquery = Inventory.objects.filter(
                product=OuterRef('pk'),
                store_id=store_id
            ).values('quantity')[:1]
            queryset = queryset.annotate(
                inventory_quantity=Coalesce(Subquery(inventory_subquery), 0, output_field=IntegerField())
            )

        # 6. Apply database-agnostic relevance scoring if search active
        if q:
            queryset = queryset.annotate(
                relevance_score=Case(
                    When(title__iexact=q, then=Value(10)),
                    When(title__istartswith=q, then=Value(8)),
                    When(title__icontains=q, then=Value(6)),
                    When(category__name__iexact=q, then=Value(5)),
                    When(description__icontains=q, then=Value(2)),
                    default=Value(0),
                    output_field=IntegerField()
                )
            )

        # 7. Sorting
        sort_param = self.request.query_params.get('sort', 'relevance')
        if sort_param == 'price':
            queryset = queryset.order_by('price')
        elif sort_param == '-price':
            queryset = queryset.order_by('-price')
        elif sort_param == 'newest':
            queryset = queryset.order_by('-created_at')
        elif sort_param == 'relevance' and q:
            queryset = queryset.order_by('-relevance_score', 'title')
        else:
            queryset = queryset.order_by('title')

        return queryset

@extend_schema(
    parameters=[
        OpenApiParameter(name='q', type=str, required=True, description="Query prefix (minimum 3 characters)"),
    ],
    responses={200: list[str]},
    description="Lightweight prefix-first autocomplete suggestions returning up to 10 unique matching product titles."
)
class AutocompleteView(APIView):
    """
    Endpoint: GET /api/search/suggest/?q=xxx
    Autocomplete suggestions returning up to 10 product titles.
    Throttled at 20 requests/minute per IP, cached using Redis.
    """
    throttle_classes = [SuggestRateThrottle]

    def get(self, request, *args, **kwargs):
        q = request.query_params.get('q', '').strip()
        
        # Enforce minimum of 3 characters
        if len(q) < 3:
            return Response(
                {"error": "Minimum 3 characters required for suggestions."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Caching logic
        cache_key = f"suggest:q:{q.lower()}"
        cached_titles = cache.get(cache_key)
        if cached_titles is not None:
            # Let the dashboard know if it came from cache
            response = Response(cached_titles)
            response['X-Cache'] = 'HIT'
            return response

        # Query Database
        # Filter products containing the keyword in their title
        queryset = Product.objects.filter(title__icontains=q)

        # Prefix matches should appear before general matches
        queryset = queryset.annotate(
            is_prefix=Case(
                When(title__istartswith=q, then=Value(True)),
                default=Value(False),
                output_field=BooleanField()
            )
        ).order_by('-is_prefix', 'title')[:50]  # Fetch a larger slice to account for potential duplicates

        # Extract unique titles while preserving the prefix-first sort order
        titles = []
        for title in queryset.values_list('title', flat=True):
            if title not in titles:
                titles.append(title)
                if len(titles) == 10:
                    break

        # Store in Redis cache for 5 minutes
        cache.set(cache_key, titles, timeout=300)

        response = Response(titles)
        response['X-Cache'] = 'MISS'
        return response
