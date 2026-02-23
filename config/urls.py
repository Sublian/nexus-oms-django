from django.contrib import admin
from django.urls import path, include

from rest_framework.routers import DefaultRouter
from src.interfaces.api.views import ProductViewSet, OrderViewSet, ReportViewSet

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'reports', ReportViewSet, basename='report')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include(router.urls)),
]
