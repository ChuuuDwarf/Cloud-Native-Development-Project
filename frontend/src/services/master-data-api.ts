import { httpClient } from "@/api/httpClient";
import type { ApiResponse } from "@/types/api";

export interface MasterDataRole {
  id: string;
  name: string;
  description: string;
  permissions: string[];
}

export interface MasterDataPermission {
  id: string;
  code: string;
  description: string;
}

export interface MasterDataLab {
  id: string;
  code: string;
  name: string;
  capacity: number;
}

export interface MasterDataDepartment {
  id: string;
  code: string;
  name: string;
}

export interface MasterDataStorageLocation {
  id: string;
  code: string;
  name: string;
  description: string;
}

export interface MasterData {
  roles: MasterDataRole[];
  permissions: MasterDataPermission[];
  labs: MasterDataLab[];
  departments: MasterDataDepartment[];
  storageLocations: MasterDataStorageLocation[];
  experimentItems: string[];
  orderStatuses: string[];
  wipStatuses: string[];
  machineStatuses: string[];
  reportStatuses: string[];
  issueStatuses: string[];
  issueTypes: string[];
  notificationStatuses: string[];
  userStatuses: string[];
  severities: string[];
}

export const masterDataApi = {
  async fetch(): Promise<MasterData> {
    const res = await httpClient.get<ApiResponse<MasterData>>("/master-data");
    return res.data.data;
  },
};
