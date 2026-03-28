from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# @login_required  # Descomenta esto cuando tengas el sistema de auth listo
def dashboard_home(request):
    """
    Renderiza la página de inicio del Dashboard.
    No necesitamos pasar 'tenant' porque el Context Processor lo hace por nosotros.
    """
    return render(request, 'pages/dashboard_home.html')