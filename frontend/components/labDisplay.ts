export const labNames: Record<string, string> = {
  "LAB-A": "材料分析實驗室",
  "LAB-B": "結構分析實驗室",
  "LAB-C": "光學量測實驗室",
};

export function formatLab(lab?: string | null) {
  if (!lab) return "全 LAB";
  return `${lab} ${labNames[lab] ?? ""}`.trim();
}
