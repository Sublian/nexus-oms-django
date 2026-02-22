from django.contrib import admin
from django.urls import path, include

from rest_framework.routers import DefaultRouter
from src.interfaces.api.views import ProductViewSet

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include(router.urls)),
]
