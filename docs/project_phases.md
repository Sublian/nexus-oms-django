🎯 Fase 1: Completar el MVP Funcional - Plan de Acción Detallado

📊 BLOQUE 1: Estabilización y Cierre del Core de Órdenes ✅ COMPLETO
Objetivo: Que el ciclo de vida de la orden sea un camino feliz completo y sin cabos sueltos visibles, y que el modal de pago tenga sentido funcional.

Por qué va primero: Es el corazón del OMS. Cualquier feature nueva se construye sobre la certeza de que el flujo base funciona.

1.1 ✅ Completar transiciones de estado faltantes
Tarea: Revisar el STATUS_CHOICES y VALID_TRANSITIONS actuales en el modelo Order. Completar todas las transiciones lógicas posibles (ej: shipped → delivered, cancelled no puede ir a ningún lado, ¿puede draft ir directamente a cancelled?).

Archivos objetivo: src/domain/models/sales/order.py (o donde esté definido).

Validación: Un test unitario por cada transición. Si no tienes tests para esto, este es el momento. Es crítico.

**Status:** DONE — VALID_TRANSITIONS dict cubre DRAFT→PENDING→PAID→SHIPPED→DELIVERED→COMPLETED con ramas COURTESY, RETURNED, CANCELLED.

1.2 ✅ Refinar el modal de pago con estado real
Situación actual: El modal tiene 4 tipos de pago (efectivo, tarjeta, yape/plin, transferencia), pero no hay pasarela real. Eso está bien para un MVP.

Tarea: Asegurar que al "confirmar" el pago en el modal, la orden pase efectivamente a estado paid (o el que corresponda) y se registre un objeto Payment vinculado a la orden con payment_method y amount.

Mejora sutil pero poderosa: Agregar un campo reference_code en el modelo Payment (para número de operación de Yape/transferencia) que el operador pueda llenar manualmente. Esto simula un flujo real sin pasarela.

Archivos objetivo: Vista parcial del modal, modelo Payment, lógica de cambio de estado en el servicio de órdenes.

**Status:** DONE — Payment model registra método, monto, referencia, comisión. Modal de pago transiciona a PAID con validación de stock. transaction_reference captura operación manual.

1.3 ✅ Edición de OrderItem en órdenes no finalizadas
Tarea: Permitir que en órdenes en estado draft o pending, el operador pueda editar cantidad o eliminar un OrderItem desde la vista de detalle de la orden. Esto cierra el flujo de "me equivoqué al crear la orden".

UI: Un ícono de lápiz en cada línea que con HTMX reemplace la fila por un mini-formulario inline. Sin recarga de página.

Archivos objetivo: Vista de detalle de orden, template parcial para edición inline.

**Status:** DONE — 
  - `/orders/{id}/items/{item_id}/edit/` → inline form HTMX, valida stock al aumentar qty
  - `/orders/{id}/items/{item_id}/delete/` → elimina item, restaura stock, recalcula totales
  - `_recalculate_order_totals()` helper recalcula subtotal/IGV/total
  - Order detail modal muestra íconos lápiz/basura (solo DRAFT/PENDING)

1.4 ✅ Validación de stock antes de cambiar a estado que consume inventario
Pregunta clave: ¿En qué estado se descuenta el inventario? Probablemente en paid o shipped. Sea cual sea, debe haber una validación previa.

Tarea: En el servicio que maneja la transición, verificar que cada OrderItem tenga stock suficiente en su producto. Si no, retornar un error que HTMX muestre como un toast o mensaje flash, impidiendo la transición.

Archivos objetivo: src/application/services/order_service.py, vista de cambio de estado.

**Status:** DONE (adaptado) — Stock se decrementa al crear orden (DRAFT) usando signal + select_for_update. Validaciones:
  - order_create_view: verifica stock antes de crear OrderItem
  - order_item_edit_view: valida stock al aumentar cantidad
  - order_pay_modal_view: sanity check (stock no negativo) antes de PAID
  - Signal: usa select_for_update para atomicidad
  - Bonus: fixed double-decrement bug (stock decremented 2x before)

✅ Checkpoint Bloque 1: Una orden puede crearse, editarse en draft, pagarse (con método registrado), y cambiar de estado sin inconsistencias. El inventario se respeta. **COMPLETADO 100%.**

**Funcionalidades adicionales implementadas:**
- ✅ Edit inline de items con validación de stock (partial modal update)
- ✅ Delete de items con auto-cancelación si orden queda vacía
- ✅ Campo `nota` obligatorio al borrar último item (explicación de cambio)
- ✅ Stock restoration automático en CANCELLED
- ✅ 61 tests passing (83% → 91% coverage)

🔔 BLOQUE 2: Activar el Sistema de Notificaciones (3-4 días)
Objetivo: Darle vida al Strategy Pattern de notificaciones con un canal real (email) y conectarlo a los eventos de dominio.

Por qué va segundo: La lógica de negocio ya existe (transiciones de estado). Las notificaciones son la consecuencia natural. Además, el Strategy Pattern ya está parcialmente implementado, solo necesita "encenderse".

2.1 Conectar el Strategy Pattern a las transiciones de orden
Situación actual: Tienes la estructura del patrón pero no está totalmente configurado. Existen tareas como process_order_notifications en notification tasks.

Tarea 2.1a: Definir los eventos de dominio que disparan notificaciones:

order.confirmed → Email al cliente: "Tu pedido #123 ha sido confirmado"

order.paid → Email al cliente: "Pago recibido para pedido #123"

order.shipped → Email al cliente: "Tu pedido #123 está en camino"

order.delivered → Email al cliente: "Pedido #123 entregado. ¿Todo bien?"

order.cancelled → Email al cliente: "Pedido #123 cancelado"

Tarea 2.1b: En el OrderService, justo después de ejecutar order.transition_to(new_status), disparar el evento de dominio correspondiente que la tarea de Celery process_order_notifications escuche.

Archivos objetivo: src/application/services/order_service.py, src/infrastructure/tasks/notification_tasks.py, módulo de estrategias de notificación.

2.2 Implementar el canal Email con plantillas HTML
Tarea 2.2a: Crear una estrategia concreta EmailNotificationStrategy que herede de tu clase base. Debe aceptar un destinatario, asunto y cuerpo HTML.

Tarea 2.2b: Crear plantillas de email simples pero profesionales usando django.template.loader.render_to_string. Una plantilla base con header, footer y colores de marca, y templates específicos para cada evento.

Tarea 2.2c: Configurar Django email backend. Para desarrollo, usar django.core.mail.backends.console.EmailBackend (los emails se imprimen en consola). Para producción futura, en .env estarán las credenciales SMTP.

Archivos objetivo: src/domain/strategies/email_notification.py, templates/emails/, config/settings.py.

2.3 Agregar notificación interna para el operador (opcional, da mucho brillo)
Tarea: Cuando una orden pasa a courtesy o returned, ¿debería alguien del equipo saberlo? Un simple toast en el dashboard para el tenant sería espectacular, pero manteniéndolo simple: una tarea de Celery que registre en un modelo Notification interno.

Modelo nuevo sugerido: InternalNotification(to_user, message, is_read, created_at).

UI: Un ícono de campana en el navbar con contador de no leídas. HTMX polling cada 30 segundos para actualizar el contador.

✅ Checkpoint Bloque 2: Al cambiar el estado de una orden desde el dashboard (con HTMX), el cliente recibe un email (visible en consola de desarrollo). El operador ve notificaciones internas.

📦 BLOQUE 3: Refinamiento del Módulo de Productos y Búsqueda (2-3 días)
Objetivo: Que el módulo de productos, que ya está en estado básico-intermedio, sea una herramienta de trabajo ágil para el operador al crear/editar órdenes.

Por qué va tercero: La creación de órdenes depende de encontrar productos rápido. Sin esto, el flujo se siente lento.

3.1 Búsqueda de productos en la creación de orden
Situación actual: No sé si existe, pero si no, es crítico.

Tarea: En el formulario de creación de orden o al agregar items, implementar un campo de búsqueda con sugerencias (typeahead/autocomplete). Usando HTMX: el operador escribe 3+ caracteres, se hace una petición GET a un endpoint que devuelve un <ul> con las coincidencias, y se inyecta debajo del input.

Endpoint nuevo: /api/products/search/?q=term&tenant_id=X (o usando el tenant del request).

Archivos objetivo: Vista de creación de orden, nueva vista parcial para resultados de búsqueda.

3.2 Mejorar la vinculación producto-órdenes (dashboard inferior)
Situación actual: Al hacer click en un producto se ve un dashboard inferior con los pedidos donde está presente. Esto ya existe y es genial.

Tarea: Agregar filtros en ese dashboard inferior: por estado de orden, por rango de fechas. Que sean filtros HTMX que actualicen solo esa sección.

Extra: Mostrar total de unidades vendidas de ese producto y monto total generado (esto conecta con el FinanceService del futuro).

3.3 Variantes de producto (si aplica al alcance)
Pregunta: ¿Los productos de los tenants suelen tener variantes (talla, color)? Si es así, este es el momento de esbozarlo. Si no, posponer para Fase 2.

Mini-plan si aplica: Modelo ProductVariant con FK a Product, campo attributes como JSON, y sku único. Al buscar productos, buscar por SKU de variante también.

✅ Checkpoint Bloque 3: Crear una orden es fluido: buscar producto, seleccionarlo, agregarlo. El dashboard de producto muestra datos útiles y filtrables.

🧪 BLOQUE 4: Pulido de UI/UX y Respuesta del Sistema (2-3 días)
Objetivo: Que cada interacción se sienta viva, rápida y profesional. Esto es lo que diferencia un proyecto funcional de uno impresionante.

Por qué va cuarto: Las funcionalidades ya están. Ahora se trata de "experiencia de desarrollador y usuario". Es el pulido final de la fase.

4.1 Indicadores de carga en interacciones HTMX
Tarea: Cada vez que se hace una petición HTMX (cambiar estado, agregar item, buscar), el elemento que disparó la acción debe mostrar un spinner o estado "cargando". HTMX tiene clases CSS automáticas: htmx-request, htmx-indicator.

Implementación: Agregar un pequeño SVG spinner en los botones y usar hx-indicator para mostrarlo/ocultarlo. Esto elimina la sensación de "¿hizo clic o no?".

4.2 Mensajes de feedback toast
Tarea: Implementar un sistema de toasts (notificaciones efímeras en esquina superior derecha) para acciones exitosas y errores. Puede ser con Alpine.js (un componente simple) o con Django messages + un script Alpine.

Implementación sugerida con Alpine.js:

html
<div x-data="{ toasts: [] }" @new-toast.window="toasts.push($event.detail); setTimeout(() => toasts.shift(), 3000)">
  <template x-for="toast in toasts">
    <div class="toast" :class="toast.type" x-text="toast.message"></div>
  </template>
</div>
Y en la respuesta HTMX, incluir un header HX-Trigger: {"new-toast": {"type": "success", "message": "Estado actualizado"}}.

4.3 Validaciones del lado del servidor visibles en el modal
Tarea: En el modal de pago, si el monto es 0 o el método no es válido, mostrar errores inline junto a los campos sin recargar la página entera. HTMX permite re-renderizar solo el formulario dentro del modal manteniendo los valores ingresados.

4.4 Dashboard inicial con métricas rápidas (quick win)
Situación actual: Dashboard muestra últimas órdenes con paginación. Es funcional.

Mejora sutil: Agregar arriba 4 tarjetas pequeñas con:

Órdenes hoy

Órdenes pendientes

Ingresos hoy (suma de amount de payments del día)

Tasa de cambio actual (ya tienes ExchangeService y la tarea sync_daily_exchange_rate)

Estas tarjetas se actualizan con HTMX polling cada 60 segundos. Muestra datos vivos.

✅ Checkpoint Bloque 4: El sistema se siente reactivo, profesional. Cada acción tiene feedback visual inmediato.

📅 Cronograma Estimado Total: 10-15 días
Bloque	Días	Dependencia
1. Core de Órdenes	3-5	Ninguna
2. Notificaciones	3-4	Bloque 1
3. Productos y Búsqueda	2-3	Ideal después del 1
4. UI/UX Pulido	2-3	Bloques 1, 2, 3
Consejo táctico: Si tienes tiempo limitado, comienza un sábado con el Bloque 1 completo. El domingo avanza el 2. El siguiente fin de semana los Bloques 3 y 4. Commit a commit, el proyecto se transforma.