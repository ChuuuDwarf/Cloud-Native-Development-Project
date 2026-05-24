import type { Candidate, RequestedExperiment, Sample, Transfer, Wip } from '../types'

export function normalizeLab(value: string | null | undefined) {
  return (value ?? '').trim().toLowerCase()
}

export function normalizeExperiment(value: string | null | undefined) {
  return (value ?? '').trim().toLowerCase()
}

export function parseExperimentsFromSummary(summary: string | null): RequestedExperiment[] {
  if (!summary) return []

  return summary
    .split('、')
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => {
      const [labName, ...rest] = part.split(':')
      const experimentItem = rest.join(':').trim()

      if (!labName || !experimentItem) return null

      return {
        lab_name: labName.trim(),
        experiment_item: experimentItem,
      }
    })
    .filter((item): item is RequestedExperiment => Boolean(item))
}

export function getRequestedExperiments(sample: Sample | null): RequestedExperiment[] {
  if (!sample) return []

  // note 是使用者備註，不解析。
  // 交接流程需要的實驗順序統一從 sample.experiment_item 解析。
  return parseExperimentsFromSummary(sample.experiment_item)
}

export function findMatchingWipForExperiment(
  sampleWips: Wip[],
  experiment: RequestedExperiment,
) {
  return (
    sampleWips.find(
      (wip) =>
        normalizeLab(wip.lab_name) === normalizeLab(experiment.lab_name) &&
        normalizeExperiment(wip.experiment_item) ===
          normalizeExperiment(experiment.experiment_item),
    ) ?? null
  )
}

export function isExperimentCompleted(
  sampleWips: Wip[],
  experiment: RequestedExperiment,
) {
  return sampleWips.some(
    (wip) =>
      normalizeLab(wip.lab_name) === normalizeLab(experiment.lab_name) &&
      normalizeExperiment(wip.experiment_item) ===
        normalizeExperiment(experiment.experiment_item) &&
      wip.status === 'completed',
  )
}

export function findCompletedTransferBoundaryIndex(
  requestedExperiments: RequestedExperiment[],
  sampleWips: Wip[],
  currentLab: string,
) {
  let currentLabCompletedBoundary = -1

  for (let index = 0; index < requestedExperiments.length; index += 1) {
    const experiment = requestedExperiments[index]

    if (!isExperimentCompleted(sampleWips, experiment)) {
      break
    }

    if (normalizeLab(experiment.lab_name) === normalizeLab(currentLab)) {
      currentLabCompletedBoundary = index
    }
  }

  return currentLabCompletedBoundary
}

export function formatDateTime(value: string | null | undefined) {
  if (!value) return '-'

  try {
    return new Date(value).toLocaleString('zh-TW', {
      hour12: false,
    })
  } catch {
    return value
  }
}

export function getCandidateKey(candidate: Candidate) {
  if (candidate.kind === 'transfer') {
    return `transfer-${candidate.sample.id}-${candidate.nextWip?.id ?? `${candidate.nextLab}-${candidate.nextExperiment.experiment_item}`}`
  }

  return `return-${candidate.sample.id}`
}
