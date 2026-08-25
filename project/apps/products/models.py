import logging

from django.db import models

logger = logging.getLogger(__name__)

class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

class Product(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

# Cache invalidation signals to keep autocomplete data consistent
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

@receiver(post_save, sender=Product)
@receiver(post_delete, sender=Product)
def invalidate_autocomplete_cache(sender, instance, **kwargs):
    """
    Clears autocomplete suggest caches in Redis.
    Uses pattern matching for django-redis, with a fallback to cache.clear()
    for local backend (like testing/development using LocMemCache).
    """
    try:
        cache.delete_pattern("suggest:q:*")
    except AttributeError:
        cache.clear()
    except Exception:
        logger.exception("Failed to invalidate autocomplete cache.")
