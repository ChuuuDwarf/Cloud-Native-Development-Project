import type { OthersData } from "../types";

export function formatRequestedExperiments(order: OthersData["orders"][number]) {
  if (order.requested_experiments && order.requested_experiments.length > 0) {
    return order.requested_experiments
      .map((item) => `${item.lab_name}:${item.experiment_item}`)
      .join("、");
  }

  if (order.target_lab || order.test_item) {
    return `${order.target_lab ?? "-"}:${order.test_item ?? "-"}`;
  }

  return "-";
}
