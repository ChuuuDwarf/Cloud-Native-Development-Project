export type ExperimentRequirement = {
  lab_name: string;
  experiment_item: string;
  route_prefix?: string;
};

const ROUTE_PREFIX_PATTERN = /^([^|]+)\|(.+)$/;

export function stripExperimentRoutePrefix(value: string) {
  const trimmed = value.trim();
  const match = trimmed.match(ROUTE_PREFIX_PATTERN);

  if (!match) {
    return {
      value: trimmed,
      route_prefix: undefined,
    };
  }

  return {
    value: match[2].trim(),
    route_prefix: match[1].trim(),
  };
}

export function parseExperimentSummary(summary: string | null | undefined): ExperimentRequirement[] {
  if (!summary) return [];

  return summary
    .split("、")
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => {
      const { value, route_prefix } = stripExperimentRoutePrefix(part);
      const separatorIndex = value.indexOf(":");

      if (separatorIndex === -1) return null;

      const labName = value.slice(0, separatorIndex).trim();
      const experimentItem = value.slice(separatorIndex + 1).trim();

      if (!labName || !experimentItem) return null;

      return {
        lab_name: labName,
        experiment_item: experimentItem,
        route_prefix,
      };
    })
    .filter((item): item is ExperimentRequirement => Boolean(item));
}

export function formatExperimentSummary(summary: string | null | undefined) {
  const parsed = parseExperimentSummary(summary);

  if (parsed.length === 0) {
    return summary?.trim() || "-";
  }

  return parsed.map((item) => `${item.lab_name}:${item.experiment_item}`).join("、");
}
