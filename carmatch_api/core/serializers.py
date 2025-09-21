"""
Django REST Framework serializers for CarMatch models.

These serializers convert model instances to and from JSON representations.
You can customize the fields exposed by each serializer and nest related
serializers to include associated data in API responses.
"""

from rest_framework import serializers
from .models import (
    Category,
    Brand,
    Store,
    User,
    Vehicle,
    Product,
    Specification,
    Compatibility,
    OfferProduct,
    PriceHistorical,
    StockHistorical,
    ShippingOption,
    Service,
    ProductService,
    ExternalRating,
    Review,
    Favorite,
    PriceAlert,
    ClickOut,
)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'parent']


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ['id', 'name']


class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ['id', 'name', 'website', 'reputation', 'payment_methods']


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'phone', 'role', 'created_at']


class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = ['id', 'user', 'brand', 'model',
                  'year', 'engine', 'license_plate']


class SpecificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Specification
        fields = ['id', 'product', 'key', 'value', 'unit']


class CompatibilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Compatibility
        fields = [
            'id', 'product', 'vehicle_brand', 'vehicle_model',
            'year_from', 'year_to', 'engine'
        ]


class ProductSerializer(serializers.ModelSerializer):
    specifications = SpecificationSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'category', 'brand', 'name', 'sku', 'description',
            'warranty_months', 'created_at', 'specifications'
        ]


class OfferProductSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    store = StoreSerializer(read_only=True)

    class Meta:
        model = OfferProduct
        fields = [
            'id', 'product', 'store', 'url', 'current_availability',
            'return_policy', 'estimated_delivery', 'estimated_shipping_cost',
            'created_at'
        ]


class PriceHistoricalSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceHistorical
        fields = ['id', 'offer', 'price', 'currency',
                  'price_before', 'discount_pct', 'valid_at']


class StockHistoricalSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockHistorical
        fields = ['id', 'offer', 'status', 'quantity', 'valid_at']


class ShippingOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingOption
        fields = ['id', 'offer', 'provider', 'cost', 'estimated_time']


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'name', 'description']


class ProductServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductService
        fields = ['id', 'product', 'service', 'estimated_cost']


class ExternalRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalRating
        fields = ['id', 'offer', 'product', 'source',
                  'rating', 'reviews_count', 'snapshot_date']


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['id', 'user', 'product', 'rating', 'comment', 'created_at']


class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favorite
        fields = ['id', 'user', 'product', 'added_at']


class PriceAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceAlert
        fields = ['id', 'user', 'product', 'threshold',
                  'currency', 'active', 'created_at']


class ClickOutSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClickOut
        fields = ['id', 'user', 'offer', 'timestamp', 'referer',
                  'utm_source', 'utm_medium', 'utm_campaign']
