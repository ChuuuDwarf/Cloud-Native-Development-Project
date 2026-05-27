import { templateStoragePrefix } from "../constants";
import type { FormItem, OrderTemplate } from "../types";

export function templateStorageKey(applicantId: string) {
  return `${templateStoragePrefix}:${applicantId || "anonymous"}`;
}

export function readTemplates(applicantId: string): OrderTemplate[] {
  if (typeof window === "undefined") return [];

  try {
    const raw = window.localStorage.getItem(templateStorageKey(applicantId));
    const parsed = raw ? (JSON.parse(raw) as OrderTemplate[]) : [];
    return Array.isArray(parsed)
      ? parsed.map((template) => ({
          ...template,
          items: Array.isArray(template.items) ? template.items.map(normalizeTemplateItem) : [],
        }))
      : [];
  } catch {
    return [];
  }
}

export function writeTemplates(applicantId: string, templates: OrderTemplate[]) {
  window.localStorage.setItem(templateStorageKey(applicantId), JSON.stringify(templates));
}

function normalizeTemplateItem(item: Partial<FormItem>): FormItem {
  return {
    sampleId: item.sampleId || "",
    sampleName: item.sampleName || "",
    labId: item.labId || "",
    experimentId: item.experimentId || "",
    targetGroup: item.targetGroup || "G1",
    target: item.target || 1,
    check: item.check ?? false,
  };
}
