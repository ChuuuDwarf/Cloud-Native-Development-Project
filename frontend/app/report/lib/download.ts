import type { Report } from "../types";

/** 產生並下載報告檔（Markdown）。純前端，不需後端檔案儲存。 */
export function downloadReport(r: Report) {
  const lines = [
    `# 實驗報告 ${r.reportId}`,
    "",
    `- 標題：${r.title}`,
    `- 委託單：${r.orderId}`,
    `- 狀態：${r.status}`,
    `- 建立者：${r.createdBy}`,
    `- 版本：v${r.versions.length}`,
    "",
    "## 摘要",
    r.summary || "—",
    "",
    "## 結論",
    r.conclusion || "—",
    "",
    "## 附件",
    r.attachments.length ? r.attachments.map((a) => `- ${a.name}`).join("\n") : "—",
    "",
    "## 實驗數據",
    ...Object.entries(r.experimentData ?? {}).flatMap(([item, fields]) => [
      `### ${item}`,
      ...Object.entries(fields).map(([k, v]) => `- ${k}：${v}`),
    ]),
    "",
    "## 版本紀錄",
    ...r.versions.map(
      (v) => `- v${v.version} · ${v.status}${v.note ? ` · ${v.note}` : ""}（${v.at} · ${v.by}）`,
    ),
    "",
  ];
  const blob = new Blob([lines.join("\n")], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${r.reportId}.md`;
  a.click();
  URL.revokeObjectURL(url);
}
