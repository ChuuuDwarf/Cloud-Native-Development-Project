import type { Candidate, RequestedExperiment, Sample, Transfer, Wip } from '../types'

export function normalizeLab(value: string | null | undefined) {
  return (value ?? '').trim().toLowerCase()
}

export function normalizeExperiment(value: string | null | undefined) {
  return (value ?? '').trim().toLowerCase()
}

export function safeParseSampleNote(note: string | null) {
  if (!note) return null

  try {
    const parsed = JSON.parse(note)

    if (!parsed || typeof parsed !== 'object') return null

    return parsed as {
      requested_experiments?: RequestedExperiment[]
      priority?: string
      sample_quantity?: string
      source?: string
    }
  } catch {
    return null
  }
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

  const parsedNote = safeParseSampleNote(sample.note)

  if (
    parsedNote?.requested_experiments &&
    Array.isArray(parsedNote.requested_experiments)
  ) {
    return parsedNote.requested_experiments.filter(
      (item) => item.lab_name && item.experiment_item,
    )
  }

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

