from enum import StrEnum


class StorageStatus(StrEnum):
    """Sample storage / pickup lifecycle states.

    Ported from Role D's flat ``app/enums.py`` (``StorageStatus``). Role D used
    Chinese canonical values (實驗室 / 已入庫 / 待返還 / 已取件); to stay
    consistent with the rest of ``app.common.enums`` (English snake_case values
    synced to the frontend), the canonical values are English here and the
    Chinese originals are recorded in the docstrings for the migration mapping.
    """

    IN_LAB = "in_lab"  # 實驗室
    STORED = "stored"  # 已入庫
    PENDING_RETURN = "pending_return"  # 待返還
    PICKED_UP = "picked_up"  # 已取件
