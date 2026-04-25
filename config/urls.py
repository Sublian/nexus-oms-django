from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

from rest_framework.routers import DefaultRouter
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from src.interfaces.api.views import (
    ProductViewSet, OrderViewSet, ReportViewSet, OrderReturnViewSet,
    organization_settings_view, CustomTokenObtainPairView,
)
from src.interfaces.web.auth_views import LoginView, LogoutView

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'reports', ReportViewSet, basename='report')
router.register(r'order_returns', OrderReturnViewSet, basename='order_returns')

auth_urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
]

urlpatterns = [
    path('', RedirectView.as_view(url='/auth/login/', permanent=False)),
    path('admin/', admin.site.urls),

    # ── Autenticación web (sesiones) ──────────────────────────────────────────
    path('auth/', include((auth_urlpatterns, 'auth'))),

    # ── Autenticación JWT (API) ───────────────────────────────────────────────
    path('api/v1/auth/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # ── API REST ──────────────────────────────────────────────────────────────
    path('api/v1/', include(router.urls)),

    # ── Documentación (sin auth para facilitar el desarrollo) ─────────────────
    path('api/schema/', SpectacularAPIView.as_view(permission_classes=[AllowAny]), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema', permission_classes=[AllowAny]), name='swagger-ui'),

    # ── Web / HTMX ────────────────────────────────────────────────────────────
    path('dashboard/<slug:org_slug>/', include('src.interfaces.web.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
