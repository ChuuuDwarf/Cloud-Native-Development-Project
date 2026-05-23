from typing import Literal

from pydantic import BaseModel, Field


MachineStatus = Literal["閒置", "使用中", "保養中", "故障中", "停用"]
WipStatus = Literal["待派工", "排程中", "待上機"]
ScheduleStrategy = Literal[
    "FIFO", "Priority First", "Earliest Due Date", "Least Setup Change", "Hybrid"
]
UserRole = Literal[
    "廠區使用者",
    "實驗室人員",
    "實驗室小主管",
    "實驗室大主管",
    "系統管理者",
]


class Machine(BaseModel):
    machineId: str
    name: str
    lab: str
    status: MachineStatus
    supportedItems: list[str]
    utilization: int = Field(ge=0, le=100)
    owner: str
    lastMaintenance: str


class User(BaseModel):
    userId: str
    name: str
    role: UserRole
    department: str
    lab: str | None = None


class MachineCreate(BaseModel):
    machineId: str
    name: str
    lab: str
    supportedItems: list[str]
    owner: str
    utilization: int = Field(default=0, ge=0, le=100)
    lastMaintenance: str = "尚未保養"


class MachineStatusUpdate(BaseModel):
    status: MachineStatus


class MachineUpdate(BaseModel):
    name: str
    lab: str
    supportedItems: list[str]
    owner: str
    utilization: int = Field(ge=0, le=100)
    lastMaintenance: str


class Recipe(BaseModel):
    recipeId: str
    name: str
    version: str
    experimentItem: str
    machineIds: list[str]
    method: str
    parameters: dict[str, str]
    updatedBy: str
    updatedAt: str


class RecipeCreate(BaseModel):
    recipeId: str
    name: str
    version: str
    experimentItem: str
    machineIds: list[str]
    method: str
    parameters: dict[str, str] = Field(default_factory=dict)
    updatedBy: str


class Dispatch(BaseModel):
    dispatchId: str
    wipId: str
    orderId: str
    experimentItem: str
    priority: str
    lab: str
    dueAt: str
    status: WipStatus
    suggestedMachineId: str | None = None
    assignedMachineId: str | None = None
    assignedRecipeId: str | None = None
    scheduledStart: str | None = None
    scheduledEnd: str | None = None
    createdBy: str | None = None
    assignedBy: str | None = None
    strategy: str | None = None
    replanReason: str | None = None


class DispatchCreate(BaseModel):
    dispatchId: str
    wipId: str
    orderId: str
    experimentItem: str
    priority: str
    lab: str | None = None
    dueAt: str


class SuggestRequest(BaseModel):
    strategy: ScheduleStrategy = "FIFO"


class AssignRequest(BaseModel):
    machineId: str
    recipeId: str
    scheduledStart: str
    scheduledEnd: str


class ReplanRequest(BaseModel):
    reason: str
    strategy: ScheduleStrategy = "Hybrid"
