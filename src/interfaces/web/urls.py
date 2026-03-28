from django.urls import path
from .views import dashboard_home

app_name = 'web'

urlpatterns = [
    path('dashboard/', dashboard_home, name='dashboard_home'),
]