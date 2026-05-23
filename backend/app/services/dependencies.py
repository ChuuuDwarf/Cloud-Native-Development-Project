from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_sync_db
from app.repos.order_repo import OrderRepository
from app.services.order_service import OrderService


def get_order_repo(db: Session = Depends(get_sync_db)) -> OrderRepository:
    return OrderRepository(db)


def get_order_service(repo: OrderRepository = Depends(get_order_repo)) -> OrderService:
    return OrderService(repo)
