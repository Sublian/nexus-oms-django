import os
import django

# 1. Configurar el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from src.domain.models import Organization, Product, Category
from src.infrastructure.multitenancy.thread_local import set_current_organization, clear_current_organization

def run_seed():
    print("🚀 Iniciando carga de datos de prueba...")

    # 2. Obtener u crear organizaciones (usamos get_or_create para no duplicar)
    nike, _ = Organization.objects.get_or_create(name="Nike", defaults={'slug': 'nike'})
    adidas, _ = Organization.objects.get_or_create(name="Adidas", defaults={'slug': 'adidas'})

    # 3. Función auxiliar para crear productos bajo un contexto de organización
    def create_products_for_org(org, product_list):
        set_current_organization(org.id)
        print(f"📦 Creando productos para {org.name}...")
        
        for p_data in product_list:
            # Usamos update_or_create para poder correr el script varias veces sin errores
            Product.objects.update_or_create(
                sku=p_data['sku'],
                defaults={
                    'name': p_data['name'],
                    'price': p_data['price'],
                    'organization': org
                }
            )
        clear_current_organization()

    # 4. Datos de prueba
    nike_items = [
        {'name': 'Air Max 90', 'sku': 'NIKE-AM90', 'price': 120.00},
        {'name': 'Jordan Retro', 'sku': 'NIKE-JR1', 'price': 180.00},
    ]

    adidas_items = [
        {'name': 'Ultraboost 22', 'sku': 'ADI-UB22', 'price': 150.00},
        {'name': 'Stan Smith', 'sku': 'ADI-SS', 'price': 85.00},
    ]

    create_products_for_org(nike, nike_items)
    create_products_for_org(adidas, adidas_items)

    print("✅ Datos cargados exitosamente.")

if __name__ == '__main__':
    run_seed()