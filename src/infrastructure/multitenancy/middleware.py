from django.shortcuts import get_object_or_404
from .thread_local import set_current_organization

class OrganizationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Intentamos obtener la organización por un header o parámetro (ej: 'X-Org-ID')
        org_id = request.headers.get('X-Org-ID')
        
        if org_id:
            # Seteamos el contexto global para este hilo de ejecución
            set_current_organization(org_id)
        
        response = self.get_response(request)
        return response