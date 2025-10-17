"""
Django models reflecting the CarMatch MER.

This module defines models that correspond to the tables in the SQL DDL
provided in the project specification. To use these models in your
Django project, add the app containing this file to `INSTALLED_APPS` and
run `python manage.py makemigrations` followed by `python manage.py migrate`.

Note that these models are simplified in some areas for clarity. You
should adjust field types, indexes and relationships as needed for your
production system (e.g. using Django's built‑in User model, adding
choices for status fields, or creating composite indexes).
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


class Category(models.Model):
    """Hierarchical product categories."""

    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        'self', null=True, blank=True, related_name='children', on_delete=models.SET_NULL
    )

    class Meta:
        verbose_name_plural = "Categories"
        indexes = [models.Index(fields=["name"])]

    def __str__(self) -> str:
        return self.name


class Brand(models.Model):
    """Product brand (e.g. Bosch, Michelin)."""

    name = models.CharField(max_length=255, unique=True)

    def __str__(self) -> str:
        return self.name


class Store(models.Model):
    """Retail or marketplace from which an offer originates."""

    name = models.CharField(max_length=255)
    website = models.URLField(null=True, blank=True)
    reputation = models.DecimalField(
        max_digits=3, decimal_places=2, null=True, blank=True)
    payment_methods = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [('name', 'website')]

    def __str__(self) -> str:
        return self.name


class User(models.Model):
    """Custom user model for CarMatch.

    For production you may extend or reference `django.contrib.auth.models.AbstractUser`
    instead. This simplified model includes only a handful of fields.
    """

    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    password_hash = models.CharField(max_length=255)
    phone = models.CharField(max_length=50, null=True, blank=True)
    role = models.CharField(max_length=50, default='usuario')
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self) -> str:
        return self.email


class Vehicle(models.Model):
    """User's vehicle profile, used to filter products by compatibility."""

    user = models.ForeignKey(
        User, related_name='vehicles', on_delete=models.CASCADE)
    brand = models.CharField(max_length=255)
    model = models.CharField(max_length=255)
    year = models.PositiveIntegerField()
    engine = models.CharField(max_length=255, null=True, blank=True)
    license_plate = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.brand} {self.model} {self.year}"


class Product(models.Model):
    """Normalized automotive product.

    This model is distinct from the store listing (`OfferProduct`), which
    represents the same product sold by a specific retailer.
    """

    category = models.ForeignKey(
        Category, null=True, blank=True, on_delete=models.SET_NULL)
    brand = models.ForeignKey(
        Brand, null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=500)
    sku = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    warranty_months = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [models.Index(fields=["name"]), models.Index(fields=["sku"])]

    def __str__(self) -> str:
        return self.name


class Specification(models.Model):
    """Key/value attributes for a product (e.g. width=205)."""

    product = models.ForeignKey(
        Product, related_name='specifications', on_delete=models.CASCADE)
    key = models.CharField(max_length=255)
    value = models.CharField(max_length=255)
    unit = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.key}: {self.value}"


class Compatibility(models.Model):
    """Mapping from a product to vehicle model compatibility."""

    product = models.ForeignKey(
        Product, related_name='compatibilities', on_delete=models.CASCADE)
    vehicle_brand = models.CharField(max_length=255)
    vehicle_model = models.CharField(max_length=255)
    year_from = models.PositiveIntegerField(null=True, blank=True)
    year_to = models.PositiveIntegerField(null=True, blank=True)
    engine = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        indexes = [models.Index(
            fields=["product", "vehicle_brand", "vehicle_model"])]

    def __str__(self) -> str:
        range_year = ''
        if self.year_from and self.year_to:
            range_year = f" ({self.year_from}-{self.year_to})"
        return f"{self.product.name} ↔ {self.vehicle_brand} {self.vehicle_model}{range_year}"


class OfferProduct(models.Model):
    """A product listing as offered by a specific store."""

    product = models.ForeignKey(
        Product, related_name='offers', on_delete=models.CASCADE)
    store = models.ForeignKey(
        Store, related_name='offers', on_delete=models.CASCADE)
    url = models.URLField()
    current_availability = models.CharField(
        max_length=50, null=True, blank=True)
    return_policy = models.TextField(null=True, blank=True)
    estimated_delivery = models.CharField(
        max_length=255, null=True, blank=True)
    estimated_shipping_cost = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [('product', 'store', 'url')]

    def __str__(self) -> str:
        return f"{self.product.name} @ {self.store.name}"


class PriceHistorical(models.Model):
    """Historical price records for an offer."""

    offer = models.ForeignKey(
        OfferProduct, related_name='price_history', on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=10)
    price_before = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True)
    discount_pct = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True)
    valid_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-valid_at']

    def __str__(self) -> str:
        return f"{self.offer} {self.price} {self.currency} on {self.valid_at.date()}"


class StockHistorical(models.Model):
    """Historical stock status for an offer."""

    offer = models.ForeignKey(
        OfferProduct, related_name='stock_history', on_delete=models.CASCADE)
    status = models.CharField(max_length=50)
    quantity = models.IntegerField(null=True, blank=True)
    valid_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-valid_at']

    def __str__(self) -> str:
        return f"{self.offer} {self.status} on {self.valid_at.date()}"


class ShippingOption(models.Model):
    """Shipping options for an offer."""

    offer = models.ForeignKey(
        OfferProduct, related_name='shipping_options', on_delete=models.CASCADE)
    provider = models.CharField(max_length=255, null=True, blank=True)
    cost = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True)
    estimated_time = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.provider} - {self.cost}"


class Service(models.Model):
    """Additional services such as installation or alignment."""

    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)

    def __str__(self) -> str:
        return self.name


class ProductService(models.Model):
    """Many-to-many association between products and services."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    estimated_cost = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = [('product', 'service')]

    def __str__(self) -> str:
        return f"{self.product.name} ↔ {self.service.name}"


class ExternalRating(models.Model):
    """Aggregated external ratings for a product or offer.

    At least one of `offer` or `product` must be non-null. Use this
    model to store scraped ratings from Autoplanet, MercadoLibre, etc.
    """

    offer = models.ForeignKey(OfferProduct, null=True,
                              blank=True, on_delete=models.CASCADE)
    product = models.ForeignKey(
        Product, null=True, blank=True, on_delete=models.CASCADE)
    source = models.CharField(max_length=255)
    rating = models.DecimalField(
        max_digits=3, decimal_places=2, null=True, blank=True)
    reviews_count = models.IntegerField(null=True, blank=True)
    snapshot_date = models.DateField(default=timezone.now)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(models.Q(offer__isnull=False) |
                       models.Q(product__isnull=False)),
                name="externalrating_offer_or_product"
            )
        ]

    def __str__(self) -> str:
        target = self.offer or self.product
        return f"{target} rating from {self.source}"


class Review(models.Model):
    """User-generated review for a product."""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [('user', 'product')]

    def __str__(self) -> str:
        return f"{self.user.email} → {self.product.name}"


class Favorite(models.Model):
    """Products saved by a user."""

    user = models.ForeignKey(
        User, related_name='favorites', on_delete=models.CASCADE)
    product = models.ForeignKey(
        Product, related_name='favorited_by', on_delete=models.CASCADE)
    added_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [('user', 'product')]

    def __str__(self) -> str:
        return f"{self.user.email} ♥ {self.product.name}"


class PriceAlert(models.Model):
    """Price threshold notifications requested by a user."""

    user = models.ForeignKey(
        User, related_name='price_alerts', on_delete=models.CASCADE)
    product = models.ForeignKey(
        Product, related_name='price_alerts', on_delete=models.CASCADE)
    threshold = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=10, default='CLP')
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [('user', 'product')]

    def __str__(self) -> str:
        return f"{self.user.email} alert for {self.product.name} at {self.threshold} {self.currency}"


class ClickOut(models.Model):
    """User click-through events to external store pages."""

    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL)
    offer = models.ForeignKey(OfferProduct, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(default=timezone.now)
    referer = models.CharField(max_length=255, null=True, blank=True)
    utm_source = models.CharField(max_length=255, null=True, blank=True)
    utm_medium = models.CharField(max_length=255, null=True, blank=True)
    utm_campaign = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['offer', '-timestamp'])]

    def __str__(self) -> str:
        return f"Click on {self.offer} at {self.timestamp.isoformat()}"

    class ProductImage(models.Model):

        """Imagen obtenida de las tiendas."""

    product = models.ForeignKey(
        Product, related_name='images', on_delete=models.CASCADE)
    url = models.URLField()
    is_primary = models.BooleanField(default=False)
    alt_text = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [('product', 'url')]

    def __str__(self):
        return f"{self.product.name} image"
