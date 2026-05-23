from enum import Enum


class MachineStatus(str, Enum):
    IDLE = "idle"
    IN_USE = "in_use"
    MAINTENANCE = "maintenance"
    FAULTY = "faulty"
    DISABLED = "disabled"
