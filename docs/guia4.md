Ese comportamiento de Nubefact implica que tu integración debe diseñarse como:

multi-tenant por configuración dinámica

No como:

cliente singleton global

Eso sería un error serio de arquitectura.

🧠 CONTEXTO ARQUITECTÓNICO NUEVO

Con Nubefact tienes:

Compartido
api_base_url

Ejemplo:

https://api.nubefact.com/
Variable por tenant
endpoint_url
token
ruc

Eso significa:

Cada empresa necesita configuración propia.

🎯 OBJETIVO DE ESTA ETAPA

Diseñar:

1. CreateInvoiceUseCase

Responsable de orquestar facturación

2. NubefactClient

Cliente HTTP desacoplado

3. Integración con Celery

Async + retry

4. Mock provider

Para desarrollo sin credenciales

🏗️ ESTRUCTURA OBJETIVO

Siguiendo tu arquitectura:

apps/
  billing/
    application/
      use_cases/
        create_invoice_use_case.py

    domain/
      services/
        invoice_provider.py

    infrastructure/
      providers/
        nubefact/
          client.py
          mock_client.py

      tasks/
        invoice_tasks.py
🧩 BLOQUE 1 — MODELO DE CONFIGURACIÓN TENANT

Este bloque es obligatorio.

Requerimiento

Persistir configuración por empresa

Modelo
class CompanyInvoiceConfig(models.Model):
    company = models.OneToOneField(...)
    api_base_url = models.URLField()
    endpoint_url = models.CharField(max_length=255)
    token = models.CharField(max_length=255)
    enabled = models.BooleanField(default=True)
🎯 Razón

El cliente debe construirse así:

NubefactClient(config)

No así:

NubefactClient()
Métrica de éxito

✔️ Cada tenant factura con endpoint aislado

🥇 BLOQUE 2 — CONTRATO DEL PROVIDER

Nunca acoples workflow a Nubefact directo.

Interface
from abc import ABC, abstractmethod


class InvoiceProvider(ABC):

    @abstractmethod
    def create_invoice(self, order):
        pass
Beneficio

Luego puedes tener:

Nubefact
Mock
Otro proveedor futuro
🥈 BLOQUE 3 — NUBEFACT CLIENT EXACTO
Constructor
class NubefactClient(InvoiceProvider):

    def __init__(self, config, session=None):
        self.config = config
        self.session = session or requests.Session()
Endpoint real

Debe resolverse dinámicamente:

@property
def endpoint(self):
    return f"{self.config.api_base_url}/{self.config.endpoint_url}"
Payload builder

Separarlo.

def _build_payload(self, order):
    ...
create_invoice()
def create_invoice(self, order):

    payload = self._build_payload(order)

    response = self.session.post(
        self.endpoint,
        headers={
            "Authorization": self.config.token
        },
        json=payload,
        timeout=15
    )

    response.raise_for_status()

    return response.json()
Requerimientos

Debe manejar:

timeout
4xx
5xx
payload inválido
Logs obligatorios
NUBEFACT_REQUEST
NUBEFACT_SUCCESS
NUBEFACT_ERROR
🥉 BLOQUE 4 — MOCK CLIENT

Clave para tu situación actual.

Diseño
class MockNubefactClient(InvoiceProvider):

    def create_invoice(self, order):
        return {
            "status": "accepted",
            "invoice_id": f"MOCK-{order.id}"
        }
Selección por setting
USE_MOCK_NUBEFACT = True

Factory:

def get_invoice_provider(config):

    if settings.USE_MOCK_NUBEFACT:
        return MockNubefactClient()

    return NubefactClient(config)
Métrica de éxito

✔️ Todo el flujo corre sin credenciales

🏅 BLOQUE 5 — CREATEINVOICEUSECASE

Este es el núcleo.

Responsabilidades

Debe:

✔️ Resolver tenant
✔️ Obtener config
✔️ Resolver provider
✔️ Ejecutar emisión
✔️ Persistir resultado

Implementación
class CreateInvoiceUseCase:

    def execute(self, order):

        config = CompanyInvoiceConfig.objects.get(
            company=order.company
        )

        provider = get_invoice_provider(config)

        result = provider.create_invoice(order)

        self._persist_result(order, result)

        return result
Persistencia

Agregar campos:

invoice_status
invoice_external_id
invoice_payload
Estados
pending
issued
failed
cancelled
🔌 BLOQUE 6 — CELERY INTEGRATION EXACTA

Aquí haces el salto serio.

Task
@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=5
)
def create_invoice_task(self, order_id):

    order = Order.objects.get(id=order_id)

    CreateInvoiceUseCase().execute(order)
Workflow
def _trigger_invoicing(self, order):
    create_invoice_task.delay(order.id)
Requerimientos

Retry exponencial

Ejemplo:

1m
2m
4m
8m
16m
Métrica

✔️ Fallo transitorio no rompe operación

🧾 BLOQUE 7 — FAILURE STRATEGY

Obligatorio.

En task
except Exception as exc:
    order.invoice_status = "failed"
    order.save()
    raise
Distinción importante
Retryable
timeout
502
503
No retryable
400
payload inválido
auth error

Debes separar excepciones:

NubefactTemporaryError
NubefactPermanentError
📊 BLOQUE 8 — FLUJO OPERATIVO FINAL

El flujo exacto quedaría:

Order paid
   ↓
OrderWorkflowService
   ↓
_trigger_invoicing()
   ↓
Celery task
   ↓
CreateInvoiceUseCase
   ↓
Provider Factory
   ↓
Mock / Nubefact
   ↓
Persist result
🧪 BLOQUE 9 — TESTING REQUERIDO
Unit
CreateInvoiceUseCase
config encontrada
config faltante
provider error
Integration

Mock Celery eager

Validar:

order.invoice_status == "issued"
Mock provider

Validar:

invoice_external_id.startswith("MOCK")
🎯 MÉTRICAS DE ÉXITO DE ESTA ETAPA

La fase está lista si puedes responder sí a esto:

1

¿Una orden pagada dispara emisión async?

2

¿Cada tenant usa su endpoint correcto?

3

¿Si Nubefact cae, hay retry?

4

¿Puedo correr todo sin credenciales?

5

¿El workflow principal permanece intacto?

🚀 ORDEN DE IMPLEMENTACIÓN (IMPORTANTE)

Hazlo exactamente así:

Sprint 1
CompanyInvoiceConfig
MockClient
UseCase
Sprint 2
Celery task
Workflow integration
Sprint 3
Retry strategy
Exception hierarchy
Sprint 4
Nubefact real
INSIGHT FINAL

El punto más delicado de esta etapa no es Celery.

Ni Nubefact.

Es este:

resolver correctamente el tenant → provider → endpoint dinámico

Si esto queda mal diseñado, después tendrás:

❌ facturas emitidas por empresa equivocada
❌ contaminación entre tenants
❌ bugs imposibles de rastrear

Ese es el riesgo arquitectónico real de esta fase.