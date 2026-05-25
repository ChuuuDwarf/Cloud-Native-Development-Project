from enum import StrEnum


class MachineStatus(StrEnum):
    IDLE = "idle"
    IN_USE = "in_use"
    MAINTENANCE = "maintenance"
    FAULTY = "faulty"
    DISABLED = "disabled"
