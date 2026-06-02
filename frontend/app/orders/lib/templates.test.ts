import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { templateStoragePrefix } from "../constants";
import type { OrderTemplate } from "../types";
import { readTemplates, templateStorageKey, writeTemplates } from "./templates";

describe("orders/lib/templates", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });
  afterEach(() => {
    vi.restoreAllMocks();
    window.localStorage.clear();
  });

  describe("templateStorageKey", () => {
    it("namespaces by applicant, falling back to anonymous", () => {
      expect(templateStorageKey("u1")).toBe(`${templateStoragePrefix}:u1`);
      expect(templateStorageKey("")).toBe(`${templateStoragePrefix}:anonymous`);
    });
  });

  describe("writeTemplates / readTemplates", () => {
    it("round-trips templates and normalizes items", () => {
      const templates: OrderTemplate[] = [
        {
          id: "t1",
          name: "Template 1",
          createdAt: "2026-01-01",
          items: [
            // Intentionally partial item to exercise normalization defaults.
            { sampleId: "S1" } as never,
          ],
        },
      ];
      writeTemplates("u1", templates);
      const read = readTemplates("u1");
      expect(read).toHaveLength(1);
      expect(read[0].items[0]).toEqual({
        sampleId: "S1",
        sampleName: "",
        labId: "",
        experimentId: "",
        targetGroup: "G1",
        target: 1,
        check: false,
      });
    });

    it("returns [] when nothing stored", () => {
      expect(readTemplates("nobody")).toEqual([]);
    });

    it("returns [] and swallows malformed JSON", () => {
      window.localStorage.setItem(templateStorageKey("u1"), "{not json");
      expect(readTemplates("u1")).toEqual([]);
    });

    it("returns [] when stored value is not an array", () => {
      window.localStorage.setItem(templateStorageKey("u1"), JSON.stringify({ foo: 1 }));
      expect(readTemplates("u1")).toEqual([]);
    });

    it("defaults non-array template.items to []", () => {
      window.localStorage.setItem(
        templateStorageKey("u1"),
        JSON.stringify([{ id: "t", name: "n", createdAt: "x", items: "bad" }])
      );
      expect(readTemplates("u1")[0].items).toEqual([]);
    });
  });
});
