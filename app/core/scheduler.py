from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.logger import logger
from app.database import AsyncSessionLocal
from app.finance.service import FinanceService
from app.license.service import LicenseService

scheduler = AsyncIOScheduler()


async def job_deactivate_licenses():
    async with AsyncSessionLocal() as session:
        count = await LicenseService.deactivate_expired_licenses(session)
        if count > 0:
            logger.info(f'[Scheduler] {count} licenças expiradas foram desativadas.')


async def job_update_invoices():
    async with AsyncSessionLocal() as session:
        count = await FinanceService.mark_as_overdue(session)
        if count > 0:
            logger.info(f'[Scheduler] {count} faturas marcadas como vencidas.')


def start_app_scheduler():
    logger.info('[Scheduler] Iniciando o scheduler...')

    # Checar licenças: Todo dia às 02:05 AM
    scheduler.add_job(
        job_deactivate_licenses,
        CronTrigger.from_crontab('5 2 * * *'),
        id='check_licenses',
        replace_existing=True,
    )

    # Checar faturas: A cada 1 hora, no minuto 0
    scheduler.add_job(
        job_update_invoices,
        CronTrigger.from_crontab('0 * * * *'),
        id='check_invoices',
        replace_existing=True,
    )

    scheduler.start()
