
Tu insumo principal es el archivo histórico de contexto ubicado en: `docs/UNDERSTANDING_GRAPH_SNAPSHOT.md`. Tu objetivo es desmantelar ese documento estático y transformarlo en un Grafo de Conocimiento navegable y atómico bajo la estructura solicitada por el Arquitecto.

### 📋 REGLAS DE ORO DE GOBERNANZA (INMUTABLES)
1. **Un Concepto = Un Nodo:** Prohibido duplicar textos. Si un nodo necesita información de otro, usa enlaces relativos `[Texto](../ruta/nodo.md)`.
2. **Estándar de 4 Preguntas:** Cada nodo que crees debe responder exclusivamente a: ¿Qué es?, ¿Por qué existe?, ¿Con qué se relaciona?, y ¿Qué sigue?.
3. **Bloque de Cierre Obligatorio:** Todo nodo debe finalizar con las 4 líneas de control: Estado, Última actualización (2026-06-27), Responsable (Tech Lead), y Siguiente nodo recomendado.

### 📁 PASO 1: CREACIÓN DE LA RAÍZ DEL GRAFO
1. Crea el directorio `docs/knowledge_graph/` y las subcarpetas: `project/`, `architecture/`, `security/`, `domain/`, `infrastructure/`, `decisions/`.
2. Escribe `docs/knowledge_graph/README.md` detallando las directivas obligatorias de lectura para la IA.
3. Escribe `docs/knowledge_graph/INDEX.md` utilizando la estructura de 8 regiones del snapshot como mapa base de navegación.

### 🔄 PASO 2: MIGRACIÓN DE LOS 5 NODOS CORE (Materia Prima del Snapshot)
Genera e interconecta mediante Markdown puro los siguientes archivos utilizando la data del snapshot:
- `project/root.md`: Roadmap macro del proyecto.
- `architecture/root.md`: Define la arquitectura de doble interfaz (REST API con JWT + Web Dashboard con HTMX) y mapea el Stack Técnico oficial (Django 6.0.3, Celery, etc.).
- `security/root.md`: Indexa el Sector S0, el Sector S1 (marcado como Completado con evidencia de 337 tests en verde) y deja el boceto base para el inicio de S2.
- `domain/root.md`: Captura las reglas del Order Lifecycle (FSM de estados y el pipeline fiscal ortogonal de SUNAT) junto con las invariantes de stock por señales.
- `infrastructure/root.md`: Define el subsistema de persistencia (PostgreSQL + psycopg3) y la orquestación asíncrona de Celery Beat.

### 🛠️ PASO 3: REGISTRO DE DECISIÓN (ADR)
Crea el archivo `docs/knowledge_graph/decisions/ADR-001.md` titulado: "Why Nexus OMS uses Application Guards BEFORE PostgreSQL RLS", documentando la justificación de por qué la Fase S1 se ejecutó antes que la Fase S2.

Al finalizar la distribución, asegúrate de que no queden enlaces rotos. Muéstrame el reporte consolidado del Grafo de Conocimiento activo en la consola para nuestra validación final.