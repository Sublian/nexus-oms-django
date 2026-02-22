# Nexus Stack: The Modern Standard

### Frontend: HTMX & Tailwind CSS
* **Por qué:** Evitamos el "Over-engineering" de frameworks de JS. HTMX permite que el servidor envíe fragmentos de HTML directamente, reduciendo la latencia de desarrollo y mejorando el SEO y la simplicidad del estado.

### Async HTTP: HTTPX
* **Por qué:** `requests` es síncrono y bloquea el event loop. Usamos **HTTPX** dentro de nuestros servicios de infraestructura para interactuar con pasarelas de pago y APIs de terceros de forma asíncrona y eficiente.

### Task Queue: Celery & Redis
* **Por qué:** Redis actúa como broker de alta velocidad. Celery gestiona la resiliencia: si el servicio de correos cae, Celery reintenta la tarea con un "Exponential Backoff".