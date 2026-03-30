# src/interfaces/web/urls.py

from django.urls import path
from .views import dashboard_home, order_detail_partial, trigger_pdf_generation

app_name = 'web'

urlpatterns = [
    path('', dashboard_home, name='dashboard_home'),
    path('orders/<int:order_id>/', order_detail_partial, name='order_detail'),   #ordenes
    path('orders/<int:order_id>/generate-pdf/', trigger_pdf_generation, name='generate_order_pdf'), #pdf
]