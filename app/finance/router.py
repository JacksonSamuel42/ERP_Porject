import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi_pagination import Page

from app.auth.dependencies import CurrentSession, CurrentUser, allow_partner
from app.finance.schemas import (
    InvoiceLicenseResponse,
    InvoiceStatus,
    PaymentLicenseCreate,
    PaymentLicenseResponse,
)
from app.finance.service import FinanceService

router = APIRouter(prefix='/finance', tags=['Finance'])


@router.get('/invoices/{invoice_id}', response_model=InvoiceLicenseResponse)
async def get_invoice_details(
    invoice_id: uuid.UUID,
    session: CurrentSession,
    current_user: CurrentUser,
):
    """
    Retorna os detalhes de uma fatura específica, incluindo todos os pagamentos.
    """
    invoice = await FinanceService.get_invoice_with_payments(session, invoice_id)
    return invoice


@router.post(
    '/invoices/{invoice_id}/pay',
    response_model=PaymentLicenseResponse,
    dependencies=[Depends(allow_partner)],
)
async def pay_invoice(
    invoice_id: uuid.UUID,
    payment_data: PaymentLicenseCreate,
    request: Request,
    session: CurrentSession,
    current_user: CurrentUser,
):
    """
    Registra o pagamento de uma fatura e ativa a licença vinculada.
    Utilizado pelo Parceiro ou Admin para confirmar recebimento.
    """
    return await FinanceService.process_license_payment(
        session=session,
        actor_id=current_user.id,
        invoice_id=invoice_id,
        payment_method=payment_data.payment_method,
        transaction_reference=payment_data.transaction_reference,
        ip_address=request.client.host,
    )


@router.post(
    '/invoices/{invoice_id}/cancel',
    response_model=InvoiceLicenseResponse,
    dependencies=[Depends(allow_partner)],
)
async def cancel_invoice(
    invoice_id: uuid.UUID,
    reason: str,
    request: Request,
    session: CurrentSession,
    current_user: CurrentUser,
):
    """
    Cancela uma fatura que ainda não foi paga.
    """
    return await FinanceService.cancel_invoice(
        session=session,
        actor_id=current_user.id,
        invoice_id=invoice_id,
        reason=reason,
        ip_address=request.client.host,
    )


@router.post(
    '/payments/{payment_id}/refund',
    response_model=PaymentLicenseResponse,
    dependencies=[Depends(allow_partner)],
)
async def refund_payment(
    payment_id: uuid.UUID,
    reason: str,
    request: Request,
    session: CurrentSession,
    current_user: CurrentUser,
):
    """
    Realiza o estorno/reembolso de um pagamento e cancela a licença.
    """
    return await FinanceService.refund_payment(
        session=session,
        actor_id=current_user.id,
        payment_id=payment_id,
        reason=reason,
        ip_address=request.client.host,
    )


@router.get(
    '/my-invoices',
    response_model=Page[InvoiceLicenseResponse],
    dependencies=[Depends(allow_partner)],
)
async def list_my_invoices(
    session: CurrentSession,
    current_user: CurrentUser,
    status: Optional[InvoiceStatus] = None,
    search: Optional[str] = None,
):
    """
    Lista todas as faturas onde o usuário logado é o destinatário.
    """
    return await FinanceService.get_all_invoices_by_recipient(
        session=session, recipient_id=current_user.id, status=status, search=search
    )


@router.get('/revenue-summary', dependencies=[Depends(allow_partner)])
async def get_revenue_dashboard(session: CurrentSession, current_user: CurrentUser):
    """
    Retorna o resumo de faturamento para o Dashboard do Parceiro/Admin.
    """
    return await FinanceService.get_partner_revenue(session, current_user.id)
