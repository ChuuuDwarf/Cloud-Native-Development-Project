"use client";

import Btn from "@/components/ui/Btn";
import type { Strategy } from "@/types/dispatches";

export const STRATEGIES: Strategy[] = [
  "FIFO",
  "Priority First",
  "Earliest Due Date",
  "Least Setup Change",
  "Hybrid",
];

export const STRATEGY_DESCRIPTIONS: Record<Strategy, string> = {
  FIFO: "依 Dispatch ID 代表的進件順序排序",
  "Priority First": "特急、高、一般優先序排序",
  "Earliest Due Date": "交期最早的 WIP 優先",
  "Least Setup Change": "相同實驗項目集中，減少換機/換設定",
  Hybrid: "先看優先級，再看交期與實驗項目",
};

export const REPLAN_POLICIES: {
  reason: string;
  label: string;
  strategy: Strategy;
  hint: string;
}[] = [
  {
    reason: "機台故障重排",
    label: "機台故障",
    strategy: "Least Setup Change",
    hint: "集中相同項目，降低換機與換設定",
  },
  {
    reason: "特急單插單重排",
    label: "特急插單",
    strategy: "Priority First",
    hint: "特急與高優先級先排",
  },
  {
    reason: "前站延誤重排",
    label: "前站延誤",
    strategy: "Earliest Due Date",
    hint: "先救交期最近的項目",
  },
  {
    reason: "人員不足重排",
    label: "人員不足",
    strategy: "Hybrid",
    hint: "兼顧優先級、交期與同類項目",
  },
];

export default function StrategyBar({
  strategy,
  onReplan,
}: {
  strategy: Strategy;
  onReplan: (reason: string, strategy: Strategy) => void;
}) {
  return (
    <div
      style={{
        background: "var(--s1)",
        border: "1px solid var(--border2)",
        borderRadius: 12,
        padding: 12,
        marginBottom: 16,
        display: "flex",
        gap: 10,
        alignItems: "center",
      }}
    >
      <span style={{ color: "var(--text2)", fontSize: 12, flex: 1 }}>
        {STRATEGY_DESCRIPTIONS[strategy]}
      </span>
      {REPLAN_POLICIES.map((policy) => (
        <Btn
          key={policy.reason}
          small
          title={`${policy.strategy}：${policy.hint}`}
          onClick={() => onReplan(policy.reason, policy.strategy)}
        >
          {policy.label}
          <span style={{ display: "block", color: "var(--text3)", fontSize: 9 }}>
            {policy.strategy}
          </span>
        </Btn>
      ))}
    </div>
  );
}
