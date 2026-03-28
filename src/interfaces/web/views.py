from django.shortcuts import render, get_object_or_404
# Importamos el modelo si necesitas validar algo extra, 
# aunque el middleware ya debería tenerlo.

def dashboard_home(request, org_slug):
    """
    Renderiza el inicio del dashboard. 
    org_slug viene de la URL: /dashboard/mi-empresa/
    """
    return render(request, 'pages/dashboard_home.html')