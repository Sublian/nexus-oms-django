# config/urls.py

from django.contrib import admin
from django.urls import path, include

from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from src.interfaces.api.views import ProductViewSet, OrderViewSet, ReportViewSet, OrderReturnViewSet, organization_settings_view

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'reports', ReportViewSet, basename='report')
router.register(r'order_returns', OrderReturnViewSet, basename='order_returns')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include(router.urls)),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('dashboard/<slug:org_slug>/settings/', organization_settings_view, name='org-settings'),
]
