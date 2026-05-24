import { templateStoragePrefix } from "../constants";
import type { OrderTemplate } from "../types";

export function templateStorageKey(applicantId: string) {
  return `${templateStoragePrefix}:${applicantId || "anonymous"}`;
}

export function readTemplates(applicantId: string): OrderTemplate[] {
  if (typeof window === "undefined") return [];

  try {
    const raw = window.localStorage.getItem(templateStorageKey(applicantId));
    const parsed = raw ? (JSON.parse(raw) as OrderTemplate[]) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function writeTemplates(applicantId: string, templates: OrderTemplate[]) {
  window.localStorage.setItem(templateStorageKey(applicantId), JSON.stringify(templates));
}
