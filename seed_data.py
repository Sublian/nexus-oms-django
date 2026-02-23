import os
import django

# 1. Configurar el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from src.domain.models import Organization, Product, Category, Warehouse, Stock, TaxConfiguration
from src.infrastructure.multitenancy.thread_local import set_current_organization, clear_current_organization

def run_seed():
    print("🚀 Iniciando carga maestra de datos (Nexus OMS)...")

    # 2. Configuración Maestra de Organizaciones e Impuestos
    org_configs = [
        {'name': 'Tienda Principal', 'slug': 'main', 'tax': 18.00},
        {'name': 'Nike', 'slug': 'nike', 'tax': 15.00},
        {'name': 'Adidas', 'slug': 'adidas', 'tax': 15.00},
        {'name': 'Tienda Minorista', 'slug': 'minorista', 'tax': 12.00},
    ]

    # 3. Catálogos específicos
    catalogs = {
        'Nike': {
            'Calzado': [
                {'name': 'Air Max 90', 'sku': 'NIKE-AM90', 'price': 120.00},
                {'name': 'Jordan Retro', 'sku': 'NIKE-JR1', 'price': 180.00},
            ],
            'Ropa': [
                {'name': 'Camiseta Dri-FIT', 'sku': 'NIKE-DFT-01', 'price': 35.00},
            ]
        },
        'Adidas': {
            'Running': [
                {'name': 'Ultraboost 22', 'sku': 'ADI-UB22', 'price': 150.00},
            ],
            'Casual': [
                {'name': 'Stan Smith', 'sku': 'ADI-SS', 'price': 85.00},
            ]
        },
        'Tienda Minorista': {
            'Accesorios': [
                {'name': 'Gorra Genérica', 'sku': 'MIN-GOR-01', 'price': 15.00},
                {'name': 'Mochila Urbana', 'sku': 'MIN-MOCH-02', 'price': 45.00},
            ]
        },
        'Tienda Principal': {
            'Accesorios': [
                {'name': 'Gorra Nice', 'sku': 'NIC-GOR-01', 'price': 45.00},
                {'name': 'Mochila Nice', 'sku': 'NIC-MOCH-02', 'price': 85.00},
            ],
            'Casual': [
                {'name': 'Stan Smith', 'sku': 'ADI-SSP', 'price': 95.00},
            ],
            'Ropa': [
                {'name': 'Camiseta Dri-FIT', 'sku': 'NIKE-DFT-01P', 'price': 45.00},
            ]
        }
    }

    for config in org_configs:
        # A. Crear u Obtener Organización
        org, _ = Organization.objects.get_or_create(
            name=config['name'], 
            defaults={'slug': config['slug']}
        )
        
        # B. Establecer contexto para esta organización
        set_current_organization(org.id)
        print(f"🏢 Procesando: {org.name}")

        # C. Configurar Impuestos
        TaxConfiguration.objects.update_or_create(
            organization=org,
            is_default=True,
            defaults={'name': f'Impuesto {org.name}', 'rate': config['tax']}
        )

        # D. Crear Bodega
        warehouse, _ = Warehouse.objects.get_or_create(
            name=f"Bodega Central {org.name}",
            organization=org
        )

        # E. Cargar Catálogo si existe en nuestra definición
        org_catalog = catalogs.get(org.name, {})
        for cat_name, products in org_catalog.items():
            category, _ = Category.objects.get_or_create(name=cat_name, organization=org)
            
            for p_data in products:
                # Crear/Actualizar Producto
                product, _ = Product.objects.update_or_create(
                    sku=p_data['sku'],
                    defaults={
                        'name': p_data['name'],
                        'price': p_data['price'],
                        'category': category,
                        'organization': org
                    }
                )
                
                # Asignar Stock inicial (50 unidades)
                Stock.objects.update_or_create(
                    product=product,
                    warehouse=warehouse,
                    organization=org,
                    defaults={'quantity': 50}
                )

        # Limpiar contexto antes de la siguiente organización
        clear_current_organization()

    print("\n✅ Proceso de seeding finalizado con éxito.")

if __name__ == '__main__':
    run_seed()