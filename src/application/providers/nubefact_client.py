import logging

import requests

from src.domain.exceptions import NubefactTemporaryError, NubefactPermanentError
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

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=self.TIMEOUT)
        except requests.exceptions.Timeout:
            raise NubefactTemporaryError(
                f"Timeout after {self.TIMEOUT}s — order_id={order.id}"
            )
        except requests.exceptions.ConnectionError as exc:
            raise NubefactTemporaryError(
                f"Connection error — order_id={order.id}: {exc}"
            )

        logger.info(
            f"[NubefactClient][order_id={order.id}][status={response.status_code}]"
        )

        if response.status_code in _PERMANENT_CODES:
            raise NubefactPermanentError(
                f"HTTP {response.status_code} — order_id={order.id}: {response.text[:300]}"
            )

        if response.status_code in _TEMPORARY_CODES:
            raise NubefactTemporaryError(
                f"HTTP {response.status_code} — order_id={order.id}: {response.text[:300]}"
            )

        if not response.ok:
            # Cualquier otro código no-2xx no clasificado → error permanente
            raise NubefactPermanentError(
                f"HTTP {response.status_code} — order_id={order.id}: {response.text[:300]}"
            )

        data = response.json()
        serie = data.get('serie', '')
        numero = data.get('numero', '')
        external_id = f"{serie}-{numero}" if serie and numero else f"NFE-{order.id}"

        return {
            'status': 'issued',
            'external_id': external_id,
            'error': None,
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
