from .models import Product

class CatalogService:
    @staticmethod
    def create_product(organization, name, sku, price, category=None):
        """
        Lógica de negocio para crear un producto.
        Aquí podríamos añadir validaciones extra, como verificar 
        si el SKU ya existe para esa organización específica.
        """
        if price < 0:
            raise ValueError("El precio no puede ser negativo")
            
        product = Product.objects.create(
            organization=organization,
            name=name,
            sku=sku,
            price=price,
            category=category
        )
        return product