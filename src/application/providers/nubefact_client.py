import logging
import time

import requests

from src.domain.exceptions import NubefactTemporaryError, NubefactPermanentError
from src.domain.observability import classify_error, ErrorCategory
from src.domain.models.integrations import ExternalRequestLog
from .invoice_provider import InvoiceProvider

logger = logging.getLogger("nubefact_client")

# Códigos HTTP que indican error permanente (no reintentar)
_PERMANENT_CODES = {400, 401, 403, 422}
# Códigos HTTP que indican error temporal (safe to retry)
_TEMPORARY_CODES = {500, 502, 503, 504}


class NubefactClient(InvoiceProvider):
    TIMEOUT = 15  # segundos — si Nubefact no responde, liberamos el worker

    def create_invoice(self, order) -> dict:
        url = f"{self.config.api_base_url.rstrip('/')}/{self.config.endpoint_url.strip('/')}"
        headers = {
            'Authorization': f'Token {self.config.token}',
            'Content-Type': 'application/json',
        }
        payload = self._build_payload(order)

        logger.info(
            f"[NubefactClient][order_id={order.id}][action=POST][url={url}]"
        )

        start_time = time.time()
        response = None
        exception_raised = None

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=self.TIMEOUT)
        except requests.exceptions.Timeout as exc:
            duration_ms = int((time.time() - start_time) * 1000)
            category = classify_error(exc)
            error_msg = f"[{category.value}] Timeout after {self.TIMEOUT}s — order_id={order.id}"
            self._log_external_request(
                order=order,
                operation='create_invoice',
                request_payload=payload,
                response_payload=None,
                status_code=None,
                duration_ms=duration_ms,
                success=False,
                error_message=error_msg,
            )
            exception_raised = NubefactTemporaryError(error_msg)
        except requests.exceptions.ConnectionError as exc:
            duration_ms = int((time.time() - start_time) * 1000)
            category = classify_error(exc)
            error_msg = f"[{category.value}] Connection error — order_id={order.id}: {exc}"
            self._log_external_request(
                order=order,
                operation='create_invoice',
                request_payload=payload,
                response_payload=None,
                status_code=None,
                duration_ms=duration_ms,
                success=False,
                error_message=error_msg,
            )
            exception_raised = NubefactTemporaryError(error_msg)

        if exception_raised:
            raise exception_raised

        duration_ms = int((time.time() - start_time) * 1000)
        logger.info(
            f"[NubefactClient][order_id={order.id}][status={response.status_code}][duration_ms={duration_ms}]"
        )

        if response.status_code in _PERMANENT_CODES:
            category = classify_error(response.status_code)
            error_msg = f"[{category.value}] HTTP {response.status_code} — order_id={order.id}: {response.text[:300]}"
            self._log_external_request(
                order=order,
                operation='create_invoice',
                request_payload=payload,
                response_payload=response.json() if response.text else None,
                status_code=response.status_code,
                duration_ms=duration_ms,
                success=False,
                error_message=error_msg,
            )
            raise NubefactPermanentError(error_msg)

        if response.status_code in _TEMPORARY_CODES:
            category = classify_error(response.status_code)
            error_msg = f"[{category.value}] HTTP {response.status_code} — order_id={order.id}: {response.text[:300]}"
            self._log_external_request(
                order=order,
                operation='create_invoice',
                request_payload=payload,
                response_payload=response.json() if response.text else None,
                status_code=response.status_code,
                duration_ms=duration_ms,
                success=False,
                error_message=error_msg,
            )
            raise NubefactTemporaryError(error_msg)

        if not response.ok:
            category = classify_error(response.status_code)
            error_msg = f"[{category.value}] HTTP {response.status_code} — order_id={order.id}: {response.text[:300]}"
            self._log_external_request(
                order=order,
                operation='create_invoice',
                request_payload=payload,
                response_payload=response.json() if response.text else None,
                status_code=response.status_code,
                duration_ms=duration_ms,
                success=False,
                error_message=error_msg,
            )
            raise NubefactPermanentError(error_msg)

        data = response.json()
        serie = data.get('serie', '')
        numero = data.get('numero', '')
        external_id = f"{serie}-{numero}" if serie and numero else f"NFE-{order.id}"

        hash_value = data.get('hash') or data.get('hash_cpe') or data.get('hash_cdr')

        self._log_external_request(
            order=order,
            operation='create_invoice',
            request_payload=payload,
            response_payload=data,
            status_code=response.status_code,
            duration_ms=duration_ms,
            success=True,
            error_message=None,
        )

        return {
            'status': 'submitted',
            'external_id': external_id,
            'hash': hash_value,
            'error': None,
        }

    def get_invoice_status(self, order, external_id: str) -> dict:
        """
        Consulta el estado de un comprobante ya emitido en Nubefact/SUNAT.

        Nubefact expone la operacion 'consultar_comprobante' en el mismo
        endpoint base. Parsea los campos SUNAT y normaliza al contrato ABC.
        """
        url = f"{self.config.api_base_url.rstrip('/')}/{self.config.endpoint_url.strip('/')}"
        headers = {
            'Authorization': f'Token {self.config.token}',
            'Content-Type': 'application/json',
        }

        # external_id tiene forma 'B001-42' — serie y numero
        parts = external_id.split('-', 1)
        serie  = parts[0] if len(parts) == 2 else external_id
        numero = parts[1] if len(parts) == 2 else ''

        payload = {
            'operacion':           'consultar_comprobante',
            'tipo_de_comprobante': 2,
            'serie':               serie,
            'numero':              numero,
        }

        logger.info(
            f"[NubefactClient][order_id={order.id}][external_id={external_id}][action=QUERY_STATUS]"
        )

        start_time = time.time()
        response = None
        exception_raised = None

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=self.TIMEOUT)
        except requests.exceptions.Timeout as exc:
            duration_ms = int((time.time() - start_time) * 1000)
            category = classify_error(exc)
            error_msg = f"[{category.value}] Timeout querying status — external_id={external_id}"
            self._log_external_request(
                order=order,
                operation='query_status',
                request_payload=payload,
                response_payload=None,
                status_code=None,
                duration_ms=duration_ms,
                success=False,
                error_message=error_msg,
            )
            exception_raised = NubefactTemporaryError(error_msg)
        except requests.exceptions.ConnectionError as exc:
            duration_ms = int((time.time() - start_time) * 1000)
            category = classify_error(exc)
            error_msg = f"[{category.value}] Connection error querying status — external_id={external_id}: {exc}"
            self._log_external_request(
                order=order,
                operation='query_status',
                request_payload=payload,
                response_payload=None,
                status_code=None,
                duration_ms=duration_ms,
                success=False,
                error_message=error_msg,
            )
            exception_raised = NubefactTemporaryError(error_msg)

        if exception_raised:
            raise exception_raised

        duration_ms = int((time.time() - start_time) * 1000)
        logger.info(
            f"[NubefactClient][order_id={order.id}][external_id={external_id}][status={response.status_code}][duration_ms={duration_ms}]"
        )

        if response.status_code in _PERMANENT_CODES:
            category = classify_error(response.status_code)
            error_msg = f"[{category.value}] HTTP {response.status_code} querying status — external_id={external_id}: {response.text[:300]}"
            self._log_external_request(
                order=order,
                operation='query_status',
                request_payload=payload,
                response_payload=response.json() if response.text else None,
                status_code=response.status_code,
                duration_ms=duration_ms,
                success=False,
                error_message=error_msg,
            )
            raise NubefactPermanentError(error_msg)

        if response.status_code in _TEMPORARY_CODES:
            category = classify_error(response.status_code)
            error_msg = f"[{category.value}] HTTP {response.status_code} querying status — external_id={external_id}: {response.text[:300]}"
            self._log_external_request(
                order=order,
                operation='query_status',
                request_payload=payload,
                response_payload=response.json() if response.text else None,
                status_code=response.status_code,
                duration_ms=duration_ms,
                success=False,
                error_message=error_msg,
            )
            raise NubefactTemporaryError(error_msg)

        if not response.ok:
            category = classify_error(response.status_code)
            error_msg = f"[{category.value}] HTTP {response.status_code} querying status — external_id={external_id}: {response.text[:300]}"
            self._log_external_request(
                order=order,
                operation='query_status',
                request_payload=payload,
                response_payload=response.json() if response.text else None,
                status_code=response.status_code,
                duration_ms=duration_ms,
                success=False,
                error_message=error_msg,
            )
            raise NubefactPermanentError(error_msg)

        data = response.json()

        # Nubefact expone 'aceptado_por_sunat' y 'observado' en la respuesta.
        # 'observado' significa aceptado por SUNAT pero con observaciones menores.
        accepted = bool(data.get('aceptado_por_sunat', False))
        observed = accepted and bool(data.get('observado', False))
        rejected = not accepted and data.get('codigo_de_la_respuesta_sunat') not in (None, '', '0')

        hash_value = data.get('hash') or data.get('hash_cpe') or data.get('hash_cdr')
        provider_ref = data.get('enlace_del_cdi') or data.get('cadena_para_codigo_qr')

        self._log_external_request(
            order=order,
            operation='query_status',
            request_payload=payload,
            response_payload=data,
            status_code=response.status_code,
            duration_ms=duration_ms,
            success=True,
            error_message=None,
        )

        return {
            'accepted':           accepted,
            'observed':           observed,
            'rejected':           rejected,
            'hash':               hash_value,
            'provider_reference': provider_ref,
            'raw_response':       data,
        }

    def _build_payload(self, order) -> dict:
        from django.utils import timezone

        items = []
        for item in order.items.all():
            price = float(item.price_at_order)
            # IGV 18%: valor_unitario = precio / 1.18
            value_unit = round(price / 1.18, 4)
            igv_unit = round(price - value_unit, 4)

            items.append({
                'unidad_de_medida': 'NIU',
                'codigo': str(item.product.sku),
                'descripcion': str(item.product.name),
                'cantidad': item.quantity,
                'valor_unitario': value_unit,
                'precio_unitario': price,
                'subtotal': round(value_unit * item.quantity, 2),
                'tipo_de_igv': 1,
                'igv': round(igv_unit * item.quantity, 2),
                'total': round(price * item.quantity, 2),
            })

        return {
            'operacion': 'generar_comprobante',
            'tipo_de_comprobante': 2,           # 2 = boleta
            'serie': 'B001',
            'numero': order.id,
            'sunat_transaction': 1,
            'cliente_tipo_de_documento': 1,     # 1 = DNI
            'cliente_numero_de_documento': '00000000',
            'cliente_denominacion': order.customer_name,
            'cliente_email': order.customer_email,
            'fecha_de_emision': timezone.now().strftime('%d-%m-%Y'),
            'moneda': 1,                        # 1 = PEN
            'porcentaje_de_igv': 18,
            'total_gravada': float(order.subtotal),
            'total_igv': float(order.tax_amount),
            'total': float(order.total_amount),
            'detalle': items,
            'externa_id': f'ORDER-{order.id}',  # idempotency key
        }

    def _log_external_request(self, order, operation: str, request_payload: dict,
                             response_payload, status_code, duration_ms: int,
                             success: bool, error_message: str = None):
        """
        Registra cada llamada HTTP a Nubefact en ExternalRequestLog.

        Respeta tipos nativos: order_id (FK), organization_id (FK),
        duration_ms (int), error_message (text con prefijo de categoría).

        Antiduplicación: este método es el ÚNICO lugar donde se crea el log.
        """
        ExternalRequestLog.objects.create(
            organization=order.organization,
            service=None,  # nullable, no hay contexto de ExternalServiceConfig
            provider_name='nubefact',
            operation=operation,
            order=order,
            request_payload=request_payload,
            response_payload=response_payload,
            status_code=status_code,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message,
        )
