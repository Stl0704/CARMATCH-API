# core/urls.py
from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import ping, RepuestosViewSet

router = SimpleRouter()
router.register(r"repuestos", RepuestosViewSet, basename="repuestos")

urlpatterns = [
    path("ping/", ping, name="ping"),
    path("", include(router.urls)),  # /repuestos/
]
