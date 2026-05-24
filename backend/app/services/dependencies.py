from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repos.order_repo import OrderRepository
from app.services.order_service import OrderService


async def get_order_repo(db: AsyncSession = Depends(get_db)) -> OrderRepository:
    return OrderRepository(db)


def get_order_service(repo: OrderRepository = Depends(get_order_repo)) -> OrderService:
    return OrderService(repo)
