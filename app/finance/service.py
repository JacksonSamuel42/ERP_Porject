import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.models import AuditLog, PartnerProfile
from app.finance.constants import INVOCE_DUE_DAYS
from app.finance.exceptions import (
    IllegalStatusTransitionException,
    InvalidInvoiceStateException,
    InvoiceExpiredException,
    InvoiceNotFoundException,
    PaymentNotFoundException,
    PaymentRefundException,
)
from app.finance.models import (
    InvoiceLicense,
    InvoiceStatus,
    LicenseTransactionType,
    PaymentLicense,
    PaymentStatus,
)
from app.finance.utils import InvoiceUtils
from app.license.models import ClientLicense, PartnerLicense


class FinanceService:
    @staticmethod
    async def _log_action(
        session: AsyncSession,
        actor_id: uuid.UUID,
        action_type: str,
        target_id: uuid.UUID,
        details: dict,
        ip_address: Optional[str] = None,
    ):
        """Método privado para persistir logs de auditoria"""
        log = AuditLog(
            actor_id=actor_id,
            action_type=action_type,
            target_id=target_id,
            details=details,
            ip_address=ip_address,
        )
        session.add(log)

    @staticmethod
    async def create_invoice_for_license(
        session: AsyncSession,
        issuer_id: Optional[uuid.UUID],
        recipient_id: uuid.UUID,
        is_client: bool,
        actor_id: uuid.UUID,
        base_amount: float,
        partner_license_id: Optional[uuid.UUID] = None,
        client_license_id: Optional[uuid.UUID] = None,
        tax_rate: float = 14.0,
        ip_address: Optional[str] = None,
    ) -> InvoiceLicense:
        """
        Gera uma fatura para uma licença recém-criada.
        """
        totals = InvoiceUtils.calculate_invoice_totals(base_amount, tax_rate)

        new_invoice = InvoiceLicense(
            invoice_number=InvoiceUtils.generate_invoice_number(),
            issuer_id=issuer_id,
            recipient_client_id=recipient_id if is_client else None,
            recipient_partner_id=recipient_id if not is_client else None,
            base_amount=totals['base_amount'],
            tax_amount=totals['tax_amount'],
            total_amount=totals['total_amount'],
            tax_rate=totals['tax_rate'],
            status=InvoiceStatus.OPEN,
            due_date=datetime.now(timezone.utc) + timedelta(days=INVOCE_DUE_DAYS),
            notes=f'Licença gerada em {datetime.now(timezone.utc).strftime("%d/%m/%Y")}',
        )

        session.add(new_invoice)
        await session.flush()

        await FinanceService._log_action(
            session,
            actor_id,
            'INVOICE_CREATE',
            new_invoice.id,
            {'invoice_number': new_invoice.invoice_number, 'total': totals['total_amount']},
            ip_address,
        )

        return new_invoice

    @staticmethod
    async def process_license_payment(
        session: AsyncSession,
        invoice_id: uuid.UUID,
        actor_id: uuid.UUID,
        payment_method: str,
        transaction_reference: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> PaymentLicense:
        """
        Registra o pagamento de uma fatura de licença e atualiza os status.
        """
        # Buscar a fatura
        result = await session.execute(
            select(InvoiceLicense).where(InvoiceLicense.id == invoice_id)
        )
        invoice = result.scalar_one_or_none()

        if not invoice:
            raise InvoiceNotFoundException()

        if invoice.due_date < datetime.now(timezone.utc):
            invoice.status = InvoiceStatus.OVERDUE
            await session.commit()
            raise InvoiceExpiredException()

        if invoice.status != InvoiceStatus.OPEN:
            raise InvalidInvoiceStateException(invoice.status.value)

        # Criar o registro de pagamento
        # Determinamos o tipo baseado em quem é o destinatário da fatura
        tx_type = (
            LicenseTransactionType.CLIENT_LICENSE
            if invoice.recipient_client_id
            else LicenseTransactionType.PARTNER_SUBSCRIPTION
        )

        new_payment = PaymentLicense(
            type=tx_type,
            invoice_id=invoice.id,
            partner_license_id=invoice.recipient_partner_id,
            client_license_id=invoice.recipient_client_id,
            amount=invoice.total_amount,
            status=PaymentStatus.PAID,
            payment_method=payment_method,
            payment_date=datetime.now(timezone.utc),
        )

        # Ativando a licença
        activated_entity_type = None

        if invoice.partner_license_id:
            # Ativar licença do Parceiro
            partner_lic = await session.get(PartnerLicense, invoice.partner_license_id)
            if partner_lic:
                partner_lic.is_active = True
                activated_entity_type = 'PARTNER_LICENSE'
        elif invoice.client_license_id:
            # Ativar licença do Cliente
            client_lic = await session.get(ClientLicense, invoice.client_license_id)
            if client_lic:
                client_lic.is_active = True
                activated_entity_type = 'CLIENT_LICENSE'

        # Atualizar status da fatura
        invoice.status = InvoiceStatus.PAID
        session.add(new_payment)
        await session.flush()

        await FinanceService._log_action(
            session,
            actor_id,
            'PAYMENT_AND_ACTIVATION',
            new_payment.id,
            {
                'invoice_id': str(invoice_id),
                'activated_type': activated_entity_type,
                'method': payment_method,
            },
            ip_address,
        )

        await session.commit()
        await session.refresh(new_payment)

        return new_payment

    @staticmethod
    async def get_partner_revenue(session: AsyncSession, user_id: uuid.UUID):
        """
        Calcula o total faturado por um parceiro (útil para o dashboard no PySide6).
        """
        stmt = select(InvoiceLicense).where(
            InvoiceLicense.issuer_id == user_id, InvoiceLicense.status == InvoiceStatus.PAID
        )
        result = await session.execute(stmt)
        invoices = result.scalars().all()

        total = sum(inv.total_amount for inv in invoices)
        return {'user_id': user_id, 'total_revenue': total, 'count': len(invoices)}

    @staticmethod
    async def get_invoice_with_payments(
        session: AsyncSession, invoice_id: uuid.UUID
    ) -> Optional[InvoiceLicense]:
        """
        Busca uma fatura específica pelo ID e traz todos os
        pagamentos associados (relacionamento carregado).
        """
        stmt = (
            select(InvoiceLicense)
            .options(selectinload(InvoiceLicense.payments))
            .where(InvoiceLicense.id == invoice_id)
        )

        result = await session.execute(stmt)
        invoice = result.scalar_one_or_none()

        if not invoice:
            raise InvoiceNotFoundException()

        return invoice

    @staticmethod
    async def get_payment_by_id(
        session: AsyncSession, payment_id: uuid.UUID
    ) -> Optional[PaymentLicense]:
        """
        Busca um registro de pagamento específico pelo seu ID.
        """
        stmt = select(PaymentLicense).where(PaymentLicense.id == payment_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all_invoices_by_recipient(
        session: AsyncSession,
        recipient_id: uuid.UUID,
        status: Optional[InvoiceStatus] = None,
        search: Optional[str] = None,
    ):
        """
        Lista todas as faturas de um Cliente ou Parceiro específico com paginação.
        """
        is_partner = await session.get(PartnerProfile, recipient_id) is not None

        column = (
            InvoiceLicense.recipient_partner_id
            if is_partner
            else InvoiceLicense.recipient_client_id
        )

        stmt = (
            select(InvoiceLicense)
            .where(column == recipient_id)
            .order_by(InvoiceLicense.issue_date.desc())
        )

        if status:
            stmt = stmt.where(InvoiceLicense.status == status)

        if search:
            stmt = stmt.where(InvoiceLicense.invoice_number.ilike(f'%{search}%'))

        return await paginate(session, stmt)

    @staticmethod
    async def cancel_invoice(
        session: AsyncSession,
        actor_id: uuid.UUID,
        invoice_id: uuid.UUID,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> InvoiceLicense:
        """
        Cancela uma fatura aberta. Se já estiver paga, exige processo de reembolso.
        """
        invoice = await FinanceService.get_invoice_with_payments(session, invoice_id)

        if not invoice:
            raise InvoiceNotFoundException()

        if invoice.status == InvoiceStatus.PAID:
            raise IllegalStatusTransitionException('PAID', 'CANCELLED')

        old_status = invoice.status.value
        invoice.status = InvoiceStatus.CANCELLED
        invoice.notes = f'{invoice.notes or ""} | Motivo Cancelamento: {reason}'

        # Opcional: Aqui você pode disparar a lógica para desativar a licença vinculada
        # await LicenseService.deactivate_license(session, invoice.client_license_id)

        await FinanceService._log_action(
            session,
            actor_id,
            'INVOICE_CANCEL',
            invoice.id,
            {'old_status': old_status, 'reason': reason},
            ip_address,
        )

        await session.flush()
        return invoice

    @staticmethod
    async def refund_payment(
        session: AsyncSession,
        actor_id: uuid.UUID,
        payment_id: uuid.UUID,
        reason: str,
        ip_address: Optional[str] = None,
    ) -> PaymentLicense:
        """
        Processa o reembolso de um pagamento já realizado.
        """
        stmt = select(PaymentLicense).where(PaymentLicense.id == payment_id)
        result = await session.execute(stmt)
        payment = result.scalar_one_or_none()

        if not payment:
            raise PaymentNotFoundException()

        if payment.status != PaymentStatus.PAID:
            raise PaymentRefundException('Apenas pagamentos confirmados podem ser reembolsados.')

        # Atualizar o status do pagamento para REFUNDED
        payment.status = PaymentStatus.REFUNDED

        # Buscar a fatura vinculada para atualizar o status dela
        if payment.invoice_id:
            res_inv = await session.execute(
                select(InvoiceLicense).where(InvoiceLicense.id == payment.invoice_id)
            )
            invoice = res_inv.scalar_one_or_none()
            if invoice:
                invoice.status = InvoiceStatus.CANCELLED
                invoice.notes = f'{invoice.notes or ""} | Reembolsado: {reason}'

        await FinanceService._log_action(
            session,
            actor_id,
            'PAYMENT_REFUND',
            payment.id,
            {'reason': reason, 'amount': float(payment.amount)},
            ip_address,
        )

        await session.flush()
        return payment

    @staticmethod
    async def mark_as_overdue(session: AsyncSession):
        """
        Tarefa agendada (Cron) para marcar faturas vencidas.
        """
        from sqlalchemy import update

        stmt = (
            update(InvoiceLicense)
            .where(InvoiceLicense.status == InvoiceStatus.OPEN)
            .where(InvoiceLicense.due_date < datetime.now(timezone.utc))
            .values(status=InvoiceStatus.OVERDUE)
        )
        await session.execute(stmt)
        await session.commit()
