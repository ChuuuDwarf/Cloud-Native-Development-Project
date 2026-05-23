import type { CurrentUser, Sample, SampleFilter, Transfer } from '../types'
import { sampleStatusText } from '../constants'

export function getUserLab(user: CurrentUser) {
  return user.lab_name || user.department
}

export function isActiveSampleStatus(status: string) {
  return ['pending_receive', 'received', 'split', 'transferring', 'in_storage'].includes(status)
}

export function isTerminalSampleStatus(status: string) {
  return ['picked_up', 'cancelled', 'lost', 'damaged'].includes(status)
}

export function isSampleInCurrentLab(sample: Sample | null, user: CurrentUser) {
  if (!sample) return false

  if (user.role === 'system_admin') return true

  if (user.role !== 'lab_staff' && user.role !== 'lab_supervisor') {
    return false
  }

  const currentLab = getUserLab(user)
  const currentLocation = sample.current_location ?? ''

  return Boolean(currentLab && currentLocation.startsWith(currentLab))
}

export function shouldMaskSampleForLab(sample: Sample, user: CurrentUser) {
  if (user.role === 'factory_user' || user.role === 'system_admin') {
    return false
  }

  if (user.role !== 'lab_staff' && user.role !== 'lab_supervisor') {
    return false
  }

  if (isTerminalSampleStatus(sample.status)) {
    return false
  }

  return !isSampleInCurrentLab(sample, user)
}

export function getDisplaySampleStatus(
  sample: Sample,
  user: CurrentUser,
  outgoingTransfer?: Transfer,
) {
  if (sample.status === 'picked_up') return 'picked_up'
  if (sample.status === 'cancelled') return 'cancelled'
  if (sample.status === 'lost') return 'lost'
  if (sample.status === 'damaged') return 'damaged'

  if (!shouldMaskSampleForLab(sample, user)) {
    return sample.status
  }

  if (outgoingTransfer?.status === 'pending') {
    return 'transfer_pending'
  }

  if (outgoingTransfer?.status === 'transferring') {
    return 'transferred_waiting_receive'
  }

  if (outgoingTransfer?.status === 'received') {
    return 'transferred_received'
  }

  if (outgoingTransfer?.status === 'cancelled') {
    return 'cancelled'
  }

  return 'transferred_out'
}

export function getDisplaySampleLocation(
  sample: Sample,
  user: CurrentUser,
  outgoingTransfer?: Transfer,
) {
  if (sample.status === 'picked_up') {
    return sample.current_location ?? '已由使用者取回'
  }

  if (sample.status === 'cancelled') return '流程已取消'
  if (sample.status === 'lost') return '樣品異常：遺失'
  if (sample.status === 'damaged') return '樣品異常：破損'

  if (!shouldMaskSampleForLab(sample, user)) {
    return sample.current_location ?? '-'
  }

  const receiverLabText = outgoingTransfer?.to_lab
    ? `接收實驗室（${outgoingTransfer.to_lab}）`
    : '接收實驗室'

  if (outgoingTransfer?.status === 'pending') {
    return '本實驗室交接待送區'
  }

  if (outgoingTransfer?.status === 'transferring') {
    return `已送出，等待${receiverLabText}收樣`
  }

  if (outgoingTransfer?.status === 'received') {
    return `已由${receiverLabText}收樣`
  }

  if (outgoingTransfer?.status === 'cancelled') {
    return '交接已取消'
  }

  return '已離開本實驗室'
}

export function isSampleVisibleForUser(sample: Sample, user: CurrentUser) {
  if (user.role === 'system_admin') return true

  if (user.role === 'factory_user') {
    return sample.applicant_name === user.name
  }

  if (user.role === 'lab_staff' || user.role === 'lab_supervisor') {
    return true
  }

  return false
}

export function filterSamplesByView(samples: Sample[], currentUser: CurrentUser, filter: SampleFilter) {
  const visibleBase = samples.filter((sample) => isSampleVisibleForUser(sample, currentUser))

  if (currentUser.role === 'factory_user') {
    if (filter === 'active' || filter === 'current') {
      return visibleBase.filter((sample) => isActiveSampleStatus(sample.status))
    }

    if (filter === 'outbound') {
      return visibleBase.filter((sample) => sample.status === 'outbound')
    }

    if (filter === 'picked_up') {
      return visibleBase.filter((sample) => sample.status === 'picked_up')
    }

    return visibleBase
  }

  if (currentUser.role === 'lab_staff' || currentUser.role === 'lab_supervisor') {
    const currentLab = getUserLab(currentUser)

    if (filter === 'current') {
      return visibleBase.filter((sample) => {
        const location = sample.current_location ?? ''
        return currentLab && location.startsWith(currentLab) && sample.status !== 'picked_up'
      })
    }

    if (filter === 'active') {
      return visibleBase.filter((sample) => isActiveSampleStatus(sample.status))
    }

    if (filter === 'outbound') {
      return visibleBase.filter((sample) => {
        if (sample.status !== 'outbound') return false

        const currentLabName = getUserLab(currentUser)
        const location = sample.current_location ?? ''

        return Boolean(currentLabName && location.startsWith(currentLabName))
      })
    }

    if (filter === 'picked_up') {
      return visibleBase.filter((sample) => sample.status === 'picked_up')
    }

    return visibleBase
  }

  return visibleBase
}

export function formatDateTime(value: string | null) {
  if (!value) return '-'

  try {
    return new Date(value).toLocaleString('zh-TW', {
      hour12: false,
    })
  } catch {
    return value
  }
}

export function formatStatusChange(fromStatus: string | null, toStatus: string | null) {
  if (!fromStatus && !toStatus) return '狀態未變更'

  const fromText = fromStatus ? sampleStatusText[fromStatus] ?? fromStatus : '無'
  const toText = toStatus ? sampleStatusText[toStatus] ?? toStatus : '無'

  return `${fromText} → ${toText}`
}