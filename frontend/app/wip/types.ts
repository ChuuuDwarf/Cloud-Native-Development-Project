export type CurrentUser = {
  id: string
  name: string
  role: string
  role_name?: string
  department: string
  lab_name?: string | null
  email?: string
}

export type RequestedExperiment = {
  lab_name: string
  experiment_item: string
}

export type SampleNote = {
  source?: string
  sample_quantity?: string
  priority?: string
  requested_experiments?: RequestedExperiment[]
}

export type Sample = {
  id: string
  sample_no: string
  order_no: string
  sample_name: string | null
  experiment_item: string | null
  applicant_name: string | null
  applicant_department: string | null
  status: string
  current_location: string | null
  storage_location_id: string | null
  received_at: string | null
  received_by: string | null
  picked_up_at: string | null
  picked_up_by: string | null
  note: string | null
  created_at: string
  updated_at: string
}

export type Wip = {
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
  scheduled_at: string | null
  dispatched_at: string | null
  started_at: string | null
  completed_at: string | null
  terminated_at: string | null
  note: string | null
  created_at: string
  updated_at: string
}

export type WipForm = {
  lab_name: string
  experiment_item: string
  priority: string
  note: string
  auto_generated: boolean
}

