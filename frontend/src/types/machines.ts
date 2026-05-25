export type MachineStatus = "閒置" | "使用中" | "保養中" | "故障中" | "停用";

export interface Machine {
  machineId: string;
  name: string;
  lab: string;
  status: MachineStatus;
  supportedItems: string[];
  utilization: number;
  owner: string;
  lastMaintenance: string;
}

export interface MachinePayload {
  machineId: string;
  name: string;
  lab: string;
  supportedItems: string[];
  owner: string;
  utilization: number;
  lastMaintenance: string;
}
