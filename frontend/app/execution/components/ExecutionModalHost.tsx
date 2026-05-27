"use client";
import type { Machine } from "@/types/machines";
import type { Recipe } from "@/types/recipes";
import type { Wip } from "@/types/lab";
import type { ModalKind, RunFn } from "../types";
import {
  CheckinModal,
  ResultModal,
  AbortModal,
  ReviewModal,
  VerifyModal,
  DetailModal,
} from "./modals";

export default function ExecutionModalHost({
  modal,
  target,
  machines,
  recipes,
  run,
  onClose,
}: {
  modal: ModalKind;
  target: Wip | null;
  machines: Machine[];
  recipes: Recipe[];
  run: RunFn;
  onClose: () => void;
}) {
  if (!target) return null;
  if (modal === "checkin")
    return (
      <CheckinModal w={target} machines={machines} recipes={recipes} run={run} onClose={onClose} />
    );
  if (modal === "result") return <ResultModal w={target} run={run} onClose={onClose} />;
  if (modal === "abort") return <AbortModal w={target} run={run} onClose={onClose} />;
  if (modal === "review") return <ReviewModal w={target} run={run} onClose={onClose} />;
  if (modal === "verify") return <VerifyModal w={target} run={run} onClose={onClose} />;
  if (modal === "detail") return <DetailModal w={target} onClose={onClose} />;
  return null;
}
