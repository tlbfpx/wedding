"""
应收账款服务测试
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.finance.application.services import ReceivableService
from app.finance.domain.entities.enums import ReceivableStatus
from app.utils.errors import AppException


@pytest.mark.asyncio
async def test_create_receivable(db_session: AsyncSession):
    """测试创建应收记录"""
    service = ReceivableService(db_session)

    # 创建应收记录
    receivable = await service.create_receivable(
        order_id=1,
        total_amount=Decimal("10000.00"),
        due_days=30,
    )

    assert receivable.order_id == 1
    assert receivable.total_amount == Decimal("10000.00")
    assert receivable.received_amount == Decimal("0")
    assert receivable.status == ReceivableStatus.unpaid
    assert receivable.due_date is None
    assert receivable.overdue_days == 0


@pytest.mark.asyncio
async def test_create_receivable_duplicate(db_session: AsyncSession):
    """测试重复创建应收记录"""
    service = ReceivableService(db_session)

    # 第一次创建
    await service.create_receivable(
        order_id=1,
        total_amount=Decimal("10000.00"),
    )

    # 第二次创建应该失败
    with pytest.raises(AppException) as exc_info:
        await service.create_receivable(
            order_id=1,
            total_amount=Decimal("10000.00"),
        )

    assert exc_info.value.error.code == "RECEIVABLE_EXISTS"


@pytest.mark.asyncio
async def test_set_due_date(db_session: AsyncSession):
    """测试设置到期日"""
    service = ReceivableService(db_session)

    # 创建应收记录
    receivable = await service.create_receivable(
        order_id=2,
        total_amount=Decimal("10000.00"),
    )

    # 设置到期日
    updated_receivable = await service.set_due_date(
        order_id=2,
        due_days=30,
    )

    expected_due_date = date.today() + timedelta(days=30)
    assert updated_receivable.due_date == expected_due_date


@pytest.mark.asyncio
async def test_update_receivable_status_unpaid(db_session: AsyncSession):
    """测试更新应收状态 - 未收款"""
    service = ReceivableService(db_session)

    # 创建应收记录
    receivable = await service.create_receivable(
        order_id=3,
        total_amount=Decimal("10000.00"),
    )

    # 未收款状态
    await service.update_receivable_status(receivable.id)
    await db_session.refresh(receivable)

    assert receivable.status == ReceivableStatus.unpaid


@pytest.mark.asyncio
async def test_update_receivable_status_partial(db_session: AsyncSession):
    """测试更新应收状态 - 部分收款"""
    from app.finance.infrastructure.repositories import ReceivableRepository

    service = ReceivableService(db_session)
    repo = ReceivableRepository(db_session)

    # 创建应收记录
    receivable = await service.create_receivable(
        order_id=4,
        total_amount=Decimal("10000.00"),
    )

    # 部分收款
    receivable.received_amount = Decimal("5000.00")
    await repo.update(receivable)

    await service.update_receivable_status(receivable.id)
    await db_session.refresh(receivable)

    assert receivable.status == ReceivableStatus.partial


@pytest.mark.asyncio
async def test_update_receivable_status_paid(db_session: AsyncSession):
    """测试更新应收状态 - 已收款"""
    from app.finance.infrastructure.repositories import ReceivableRepository

    service = ReceivableService(db_session)
    repo = ReceivableRepository(db_session)

    # 创建应收记录
    receivable = await service.create_receivable(
        order_id=5,
        total_amount=Decimal("10000.00"),
    )

    # 全额收款
    receivable.received_amount = Decimal("10000.00")
    await repo.update(receivable)

    await service.update_receivable_status(receivable.id)
    await db_session.refresh(receivable)

    assert receivable.status == ReceivableStatus.paid


@pytest.mark.asyncio
async def test_check_overdue_receivables(db_session: AsyncSession):
    """测试检查逾期应收"""
    from app.finance.infrastructure.repositories import ReceivableRepository

    service = ReceivableService(db_session)
    repo = ReceivableRepository(db_session)

    # 创建逾期应收记录
    receivable = await service.create_receivable(
        order_id=6,
        total_amount=Decimal("10000.00"),
    )

    # 设置过期日期为昨天
    receivable.due_date = date.today() - timedelta(days=1)
    receivable.received_amount = Decimal("5000.00")  # 未全额收款
    await repo.update(receivable)

    # 检查逾期
    overdue_list = await service.check_overdue_receivables()

    assert len(overdue_list) > 0
    assert any(r.id == receivable.id for r in overdue_list)


@pytest.fixture
async def db_session():
    """创建测试数据库会话"""
    from app.database import async_session

    async with async_session() as session:
        yield session
        # 回滚以保持测试隔离
        await session.rollback()
