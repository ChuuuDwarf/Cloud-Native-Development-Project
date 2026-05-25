export type CurrentUser = {
  id: string
  name: string
  role: string
  role_name?: string | null
  department?: string | null
  lab_name?: string | null
  lab_code?: string | null
  email?: string | null
}

export type RequestedExperiment = {
  lab_name: string
  experiment_item: string
}

export type SampleData = {
  id: string
  sample_no: string
  order_no: string
  sample_name: string
  experiment_item: string
  applicant_name: string
  applicant_department: string
  status: string
  current_location: string
  note: string | null
}

export type WipData = {
  id: string
  wip_no: string
  sample_id: string
  order_no: string
  lab_name: string | null
  experiment_item: string | null
  priority: string
  status: string
  progress: number
  current_location: string | null
  completed_at: string | null
  note: string | null
  sample_no?: string | null
  sample_name?: string | null
}

export type MasterDataItem = {
  value?: string
  label?: string
  lab_name?: string
  items?: string[]
}

export type OthersData = {
  current_user: CurrentUser
  users: CurrentUser[]
  labs: Array<{
    id: string
    code?: string | null
    name: string
    description?: string | null
    capacity?: number | null
    is_active?: boolean | null
  }>
  storage_locations: Array<{
    id: string
    code: string
    name: string
    lab_name: string
    lab_code?: string | null
    area?: string | null
    is_active?: boolean | null
  }>
  orders: Array<{
    id: string
    order_no: string
    applicant_name: string
    applicant_department: string
    sample_name?: string
    sample_quantity?: string
    target_lab?: string
    test_item?: string
    priority?: string
    status: string
    requested_experiments?: RequestedExperiment[]
  }>
  samples?: SampleData[]
  wips?: WipData[]
  schedules: Array<{
    id: string
    wip_no: string
    machine_name: string
    status: string
    start_time: string | null
  }>
  dispatches: Array<{ id: string; wip_no: string; assignee_name: string; status: string }>
  issues: Array<{
    id: string
    type: string
    target_type: string
    target_no: string
    level: string
    message: string
    status: string
  }>
  master_data: Record<string, MasterDataItem[]>
}
