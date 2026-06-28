# 🕵️‍♂️ Plan de Investigación Forense: S2.1A.1 — Current Flow Discovery

**Objetivo:** Inspeccionar el repositorio de Nexus OMS para extraer evidencia física y responder el checklist de control de flujos.
**Restricción Estricta:** NO modificar código, NO crear abstracciones, NO sacar conclusiones.

## 📋 Lista de Verificación para el Operador

### 1. Contexto de Identidad
- [ ] Determinar la clase exacta en 'DEFAULT_AUTHENTICATION_CLASSES' en settings.
- [ ] Encontrar la definición física de 'organization_id' en el modelo de usuario personalizado.

### 2. Flujo del Pedido (Order ViewSet / Serializer / Model)
- [ ] Extraer el código de 'get_queryset()' del ViewSet de Pedidos.
- [ ] Extraer el código de 'perform_create()' o 'create()' del ViewSet de Pedidos.
- [ ] Verificar si existe la palabra 'organization_id' en los archivos de la app de ventas.
- [ ] Identificar si el ViewSet usa 'permission_classes' personalizadas.

### 3. Cobertura Existente
- [ ] Buscar archivos con el patrón 'test_*.py' en la aplicación de ventas que apunten a permisos o aislamiento.

*Nota para el operador: Rellena los hallazgos con código fuente extraído mediante 'cat' o 'grep'. No interpretes el resultado.*
