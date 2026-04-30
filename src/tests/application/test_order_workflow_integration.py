import logging
import pytest
from unittest.mock import MagicMock

from src.domain.models import Order
from src.domain.models.order_constants import OrderStatus
from src.application.services.order_workflow_service import OrderWorkflowService


@pytest.mark.django_db
class TestOrderWorkflowIntegration:
    # Pruebas reales con Django DB — verifica persistencia

    def test_workflow_processed_persists_to_db(self, organization):
        # Crea orden real, ejecuta workflow, verifica DB
        order = Order.objects.create(
            organization=organization,
            customer_name="Test User",
            customer_email="test@example.com",
            status=OrderStatus.PAID,
            total_amount=100,
        )

        logger = MagicMock()
        service = OrderWorkflowService(logger)

        # Ejecutar workflow
        service.handle_order_paid(order)

        # Persistencia: sin save() del servicio, el flag es True en memoria
        assert order.workflow_processed is True

        # Simular que se guardó en la vista
        order.save()

        # Refrescar desde DB
        order.refresh_from_db()

        # Verificar que persiste en DB
        assert order.workflow_processed is True

    def test_workflow_idempotency_with_real_db(self, organization):
        # Segunda ejecución en orden nuevo = no entra al flujo
        order = Order.objects.create(
            organization=organization,
            customer_name="Test User",
            customer_email="test@example.com",
            status=OrderStatus.PAID,
            total_amount=100,
        )

        logger = MagicMock()
        service = OrderWorkflowService(logger)

        # Primera ejecución
        service.handle_order_paid(order)
        order.save()
        order.refresh_from_db()

        # Reset logger para segunda llamada
        logger.reset_mock()

        # Segunda ejecución — debe ser idempotente
        service.handle_order_paid(order)

        # No debe haber llamadas a info() — solo warning
        logger.info.assert_not_called()
        warning_messages = [call.args[0] for call in logger.warning.call_args_list]
        assert any('SKIP_ALREADY_PROCESSED' in m for m in warning_messages)

    def test_workflow_does_not_execute_for_non_paid_status(self, organization):
        # Orden en estado DRAFT no debe ejecutar workflow
        order = Order.objects.create(
            organization=organization,
            customer_name="Test User",
            customer_email="test@example.com",
            status=OrderStatus.DRAFT,
            total_amount=100,
        )

        logger = MagicMock()
        service = OrderWorkflowService(logger)

        # Intentar ejecutar workflow
        service.handle_order_paid(order)

        # No debe ejecutarse
        logger.info.assert_not_called()
        warning_messages = [call.args[0] for call in logger.warning.call_args_list]
        assert any('VALIDATION_FAIL' in m for m in warning_messages)

        # Flag debe seguir en False
        assert order.workflow_processed is False

    def test_workflow_lifecycle_complete(self, organization):
        # Test del ciclo completo: crear → pagar → workflow → verificar estado
        order = Order.objects.create(
            organization=organization,
            customer_name="Test User",
            customer_email="test@example.com",
            status=OrderStatus.PENDING,
            total_amount=100,
        )

        # Transición a PAID
        order.status = OrderStatus.PAID

        # Orquestar workflow
        logger = MagicMock()
        service = OrderWorkflowService(logger)
        service.handle_order_paid(order)

        # Persistir
        order.save()

        # Verificar en DB
        order_from_db = Order.objects.get(id=order.id)
        assert order_from_db.status == OrderStatus.PAID
        assert order_from_db.workflow_processed is True
        assert order_from_db.workflow_status == 'completed'

        # Logs verifican estructura
        log_messages = [call.args[0] for call in logger.info.call_args_list]
        assert any('[action=START]' in m for m in log_messages)
        assert any('[action=END]' in m for m in log_messages)

    def test_workflow_status_marks_processing_then_completed(self, organization):
        # Verificar que workflow_status transiciona: pending → processing → completed
        order = Order.objects.create(
            organization=organization,
            customer_name="Test User",
            customer_email="test@example.com",
            status=OrderStatus.PAID,
            total_amount=100,
            workflow_status='pending'
        )

        logger = MagicMock()
        service = OrderWorkflowService(logger)
        service.handle_order_paid(order)

        order.save()
        order.refresh_from_db()

        # Verificar estado final
        assert order.workflow_status == 'completed'
        assert order.workflow_processed is True

    def test_workflow_status_on_error(self, organization):
        # Si algo falla, workflow_status = 'failed'
        order = Order.objects.create(
            organization=organization,
            customer_name="Test User",
            customer_email="test@example.com",
            status=OrderStatus.PAID,
            total_amount=100,
        )

        # Mock logger que simula error
        logger = MagicMock()
        service = OrderWorkflowService(logger)

        # Inyectar un error en _log_order_paid
        original_method = service._log_order_paid
        def failing_log(*args, **kwargs):
            raise ValueError("Simulated failure in log")
        service._log_order_paid = failing_log

        # Ejecutar y capturar error
        try:
            service.handle_order_paid(order)
        except ValueError:
            pass  # Esperado

        order.save()
        order.refresh_from_db()

        # Verificar que se marcó como fallido
        assert order.workflow_status == 'failed'
        # Pero NO se marcó como completado
        assert order.workflow_processed is False
