"""
收款服务测试
"""
import pytest
from datetime import datetime
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.finance.application.services import PaymentService
from app.finance.domain.entities.enums import PaymentMethod
from app.utils.errors import AppException


@pytest.mark.asyncio
async def test_record_payment(db_session: AsyncSession):
    """测试登记收款"""
    # 先创建应收记录
    from app.finance.application.services import ReceivableService
    from app.finance.infrastructure.repositories import ReceivableRepository

    receivable_service = ReceivableService(db_session)
    receivable_repo = ReceivableRepository(db_session)

    # 创建应收
    receivable = await receivable_service.create_receivable(
        order_id=10,
        total_amount=Decimal("10000.00"),
    )

    # 登记收款
    payment_service = PaymentService(db_session)
    payment = await payment_service.record_payment(
        order_id=10,
        amount=5000.00,
        method=PaymentMethod.transfer,
        paid_at=datetime.utcnow(),
        note="首次收款",
        created_by=1,
    )

    assert payment.order_id == 10
    assert payment.amount == 5000.00
    assert payment.method == PaymentMethod.transfer

    # 验证应收已更新
    await db_session.refresh(receivable)
    assert receivable.received_amount == Decimal("5000.00")


@pytest.mark.asyncio
async def test_record_payment_exceeds_total(db_session: AsyncSession):
    """测试收款金额超过应收"""
    from app.finance.application.services import ReceivableService

    # 创建应收记录
    receivable_service = ReceivableService(db_session)
    await receivable_service.create_receivable(
        order_id=11,
        total_amount=Decimal("10000.00"),
    )

    # 尝试收款超过应收
    payment_service = PaymentService(db_session)

    with pytest.raises(AppException) as exc_info:
        await payment_service.record_payment(
            order_id=11,
            amount=15000.00,
            method=PaymentMethod.transfer,
            paid_at=datetime.utcnow(),
        )

    assert exc_info.value.error.code == "PAYMENT_EXCEEDS_TOTAL"


@pytest.mark.asyncio
async def test_update_payment(db_session: AsyncSession):
    """测试修改收款记录"""
    from app.finance.application.services import ReceivableService

    # 创建应收并收款
    receivable_service = ReceivableService(db_session)
    await receivable_service.create_receivable(
        order_id=12,
        total_amount=Decimal("10000.00"),
    )

    payment_service = PaymentService(db_session)
    payment = await payment_service.record_payment(
        order_id=12,
        amount=5000.00,
        method=PaymentMethod.transfer,
        paid_at=datetime.utcnow(),
        created_by=1,
    )

    # 修改收款金额
    updated_payment = await payment_service.update_payment(
        payment_id=payment.id,
        amount=6000.00,
    )

    assert updated_payment.amount == 6000.00


@pytest.mark.asyncio
async def test_delete_payment(db_session: AsyncSession):
    """测试删除收款记录"""
    from app.finance.application.services import ReceivableService

    # 创建应收并收款
    receivable_service = ReceivableService(db_session)
    receivable = await receivable_service.create_receivable(
        order_id=13,
        total_amount=Decimal("10000.00"),
    )

    payment_service = PaymentService(db_session)
    payment = await payment_service.record_payment(
        order_id=13,
        amount=5000.00,
        method=PaymentMethod.transfer,
        paid_at=datetime.utcnow(),
        created_by=1,
    )

    # 删除收款
    await payment_service.delete_payment(payment.id)

    # 验证应收已扣减
    await db_session.refresh(receivable)
    assert receivable.received_amount == Decimal("0")


@pytest.fixture
async def db_session():
    """创建测试数据库会话"""
    from app.database import async_session

    async with async_session() as session:
        yield session
        await session.rollback()
