import type { UserStatus } from "@/constants/enums";

export interface RoleSummary {
  id: string;
  name: string;
}

export interface UserResponse {
  id: string;
  email: string;
  name: string;
  departmentId: string | null;
  labId: string | null;
  status: UserStatus;
  isActive: boolean;
  roles: RoleSummary[];
  createdAt: string;
  updatedAt: string;
}

export interface MeResponse {
  id: string;
  name: string;
  email: string;
  role: string;
  permissions: string[];
  labId: string | null;
  departmentId: string | null;
}

export interface CreateUserPayload {
  email: string;
  name: string;
  password: string;
  departmentId?: string | null;
  labId?: string | null;
  roleIds?: string[];
}

export interface UpdateUserPayload {
  name?: string;
  departmentId?: string | null;
  labId?: string | null;
  status?: UserStatus;
  roleIds?: string[];
  password?: string;
}

export interface ListUsersQuery {
  page?: number;
  pageSize?: number;
  keyword?: string;
  role?: string;
  departmentId?: string;
  labId?: string;
  status?: UserStatus;
}
