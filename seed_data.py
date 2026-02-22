import os
import django

# 1. Configurar el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from src.domain.models import Organization, Product, Category
from src.infrastructure.multitenancy.thread_local import set_current_organization, clear_current_organization

def run_seed():
    print("🚀 Iniciando carga de datos de prueba...")

    # 1. Obtener organizaciones
    main_shop, _ = Organization.objects.get_or_create(name="Tienda Principal", defaults={'slug': 'main'})
    nike, _ = Organization.objects.get_or_create(name="Nike", defaults={'slug': 'nike'})
    adidas, _ = Organization.objects.get_or_create(name="Adidas", defaults={'slug': 'adidas'})

    def seed_org_catalog(org, categories_data):
        set_current_organization(org.id)
        print(f"📦 Procesando catálogo para: {org.name}")
        
        for cat_name, products in categories_data.items():
            # Crear Categoría
            category, _ = Category.objects.get_or_create(
                name=cat_name, 
                organization=org
            )
            
            # Crear Productos
            for p_data in products:
                Product.objects.update_or_create(
                    sku=p_data['sku'],
                    defaults={
                        'name': p_data['name'],
                        'price': p_data['price'],
                        'category': category,
                        'organization': org
                    }
                )
        clear_current_organization()

    # 2. Definir Estructura
    nike_catalog = {
        'Calzado': [
            {'name': 'Air Max 90', 'sku': 'NIKE-AM90', 'price': 120.00},
            {'name': 'Jordan Retro', 'sku': 'NIKE-JR1', 'price': 180.00},
        ],
        'Ropa': [
            {'name': 'Camiseta Dri-FIT', 'sku': 'NIKE-DFT-01', 'price': 35.00},
        ]
    }

    adidas_catalog = {
        'Running': [
            {'name': 'Ultraboost 22', 'sku': 'ADI-UB22', 'price': 150.00},
        ],
        'Casual': [
            {'name': 'Stan Smith', 'sku': 'ADI-SS', 'price': 85.00},
        ]
    }

    # Ejecutar
    seed_org_catalog(nike, nike_catalog)
    seed_org_catalog(adidas, adidas_catalog)

    print("✅ Catálogo con categorías actualizado.")

if __name__ == '__main__':
    run_seed()