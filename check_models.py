#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.testing')
django.setup()

from src.domain.models.integrations import ExternalRequestLog
from src.domain.models import Order

print("="*80)
print("PASO 1.0: VERIFICACIÓN FÍSICA DE MODELOS")
print("="*80)

print("\n[ExternalRequestLog Fields]")
for field in ExternalRequestLog._meta.fields:
    if field.name in ('order', 'order_id', 'organization_id', 'service_id', 'service'):
        internal_type = field.get_internal_type()
        print(f"  {field.name:20} | type={internal_type:20} | null={field.null:5} | db_column={field.column}")

print("\n[Order Model - ID Field]")
for field in Order._meta.fields:
    if field.name == 'id':
        internal_type = field.get_internal_type()
        print(f"  {field.name:20} | type={internal_type:20} | {field}")

print("\n[ExternalRequestLog - Relaciones ForeignKey]")
for rel in ExternalRequestLog._meta.get_fields():
    if hasattr(rel, 'many_to_one') and rel.many_to_one:
        print(f"  {rel.name:20} | type={rel.get_internal_type():20} | null={rel.field.null}")
