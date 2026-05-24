# app/services/labs.py

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Lab


class LabService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_active_labs(self) -> list[dict]:
        labs = (
            (
                await self.session.execute(
                    select(Lab).where(Lab.is_active.is_(True)).order_by(Lab.code)
                )
            )
            .scalars()
            .all()
        )

        return [
            {
                "id": str(lab.id),
                "code": lab.code,
                "name": lab.name,
                "capacity": lab.capacity,
            }
            for lab in labs
        ]
