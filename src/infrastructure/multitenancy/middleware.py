# src/infrastructure/multitenancy/middleware.py

import re
from src.domain.models import Organization
from django.shortcuts import get_object_or_404
from .context import set_current_organization, clear_current_organization

class OrganizationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        org = None

        # 1. Try X-Org-ID header (API)
        org_id = request.headers.get('X-Org-ID')

        if org_id:
            try:
                org = Organization.objects.get(id=org_id)
            except (Organization.DoesNotExist, ValueError):
                pass

        # 2. Try URL slug (Web/Dashboard) if no org yet
        if not org:
            match = re.search(r'^/dashboard/([^/]+)/', request.path)
            if match:
                slug = match.group(1)
                try:
                    org = Organization.objects.get(slug=slug)
                except Organization.DoesNotExist:
                    pass
        
        # 3. Seteamos la organización en el request para el Context Processor
        # Y en el thread_local para la base de datos
        try:
            if org:
                request.organization = org  # 👈 ESTO alimenta al context_processor
                set_current_organization(org.id)
            else:
                request.organization = None

            response = self.get_response(request)
            return response
        finally:
            # ¡IMPORTANTE! Limpiar al terminar la petición
            clear_current_organization()