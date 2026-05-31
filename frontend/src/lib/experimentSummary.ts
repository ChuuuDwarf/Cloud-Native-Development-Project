export type ExperimentRequirement = {
  lab_name: string;
  experiment_item: string;
  route_prefix?: string;
};

const ROUTE_PREFIX_PATTERN = /^([^|]+)\|(.+)$/;

function isNonNullable<T>(value: T): value is NonNullable<T> {
  return value != null;
}

export function stripExperimentRoutePrefix(value: string): {
  value: string;
  route_prefix?: string;
} {
  const trimmed = value.trim();
  const match = trimmed.match(ROUTE_PREFIX_PATTERN);

  if (!match) {
    return {
      value: trimmed,
    };
  }

  const routePrefix = match[1]?.trim();

  return {
    value: match[2]?.trim() ?? "",
    ...(routePrefix ? { route_prefix: routePrefix } : {}),
  };
}

export function parseExperimentSummary(
  summary: string | null | undefined
): ExperimentRequirement[] {
  if (!summary) return [];

  return summary
    .split("、")
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part): ExperimentRequirement | null => {
      const { value, route_prefix } = stripExperimentRoutePrefix(part);
      const separatorIndex = value.indexOf(":");

      if (separatorIndex === -1) return null;

      const labName = value.slice(0, separatorIndex).trim();
      const experimentItem = value.slice(separatorIndex + 1).trim();

      if (!labName || !experimentItem) return null;

      return {
        lab_name: labName,
        experiment_item: experimentItem,
        ...(route_prefix ? { route_prefix } : {}),
      };
    })
    .filter(isNonNullable);
}

export function formatExperimentSummary(summary: string | null | undefined) {
  const parsed = parseExperimentSummary(summary);

  if (parsed.length === 0) {
    return summary?.trim() || "-";
  }

  return parsed.map((item) => `${item.lab_name}:${item.experiment_item}`).join("、");
}
