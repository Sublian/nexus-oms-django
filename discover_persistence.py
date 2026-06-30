import os
import sys

def main():
    # 1. Configurar el entorno de Django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
    
    # 🔥 DETECCIÓN INTELIGENTE DE ENTORNO
    # Si existe el archivo /.dockerenv, estamos dentro del contenedor
    is_inside_docker = os.path.exists('/.dockerenv')

    if not is_inside_docker:
        print("ℹ️ Ejecución en Host Local: Redirigiendo tráfico a localhost...")
        os.environ["DB_HOST"] = "localhost"
        os.environ["DATABASE_URL"] = "postgres://nexus_user:nexus_pass@localhost:5432/nexus_db"
    else:
        print("ℹ️ Ejecución dentro de Docker: Usando red interna del contenedor...")

    try:
        import django
        django.setup()
        
        # Parche dinámico solo si estamos fuera de Docker
        if not is_inside_docker:
            from django.conf import settings
            settings.DATABASES['default']['HOST'] = 'localhost'
            
        from django.db import connection
    except ImportError:
        print("❌ Error: No se pudo importar Django. Asegúrate de tener el entorno virtual activo.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error al inicializar Django: {e}")
        sys.exit(1)

    print("=" * 80)
    print("🚀 INSTRUMENTO LOCAL: DESCUBRIMIENTO ANATÓMICO DE PERSISTENCIA (S2A)")
    print("=" * 80)

    # 2. Interrogar el catálogo de PostgreSQL directamente
    query_tables = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        AND table_name NOT LIKE 'django_%'  -- Filtrado pragmático para el MVP
        AND table_name NOT LIKE 'auth_%'
        ORDER BY table_name;
    """

    try:
        with connection.cursor() as cursor:
            cursor.execute(query_tables)
            tables = [row[0] for row in cursor.fetchall()]

            print(f"📦 Se detectaron {len(tables)} tablas de negocio (excluyendo internas del framework).\n")
            print(f"{'Tabla Física':<30} | {'Columna Tenant':<18} | {'Tipo de Dato':<12} | {'Nulabilidad':<10}")
            print("-" * 80)

            for table in tables:
                # Buscar si la tabla posee columnas de tracking de organización o tenant
                query_columns = """
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    AND table_name = %s
                    AND column_name IN ('organization_id', 'tenant_id', 'company_id', 'organization');
                """
                cursor.execute(query_columns, [table])
                tenant_col = cursor.fetchone()

                if tenant_col:
                    print(f"{table:<30} | 🎯 {tenant_col[0]:<14} | {tenant_col[1]:<12} | {tenant_col[2]:<10}")
                else:
                    print(f"{table:<30} | ❌ Ninguna           | {'-':<12} | {'-':<10}")

    except Exception as e:
        print(f"❌ Error al interactuar con el catálogo de PostgreSQL: {e}")
        print("Asegúrate de que la base de datos esté corriendo y las credenciales sean correctas.")
        sys.exit(1)

    print("=" * 80)
    print("⚠️  REPORTE TEMPORAL EN CONSOLA COMPLETADO.")
    print("Ningún archivo del Knowledge Graph ha sido modificado. Listo para revisión con el Arquitecto.")
    print("=" * 80)

if __name__ == "__main__":
    main()