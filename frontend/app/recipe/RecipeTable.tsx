"use client";

import Chip from "@/components/ui/Chip";
import Panel from "@/components/ui/Panel";
import type { Recipe } from "@/types/recipes";

const HEADERS = ["Recipe", "實驗項目", "適用機台", "方法", "參數", "更新"];

export default function RecipeTable({ recipes }: { recipes: Recipe[] }) {
  return (
    <Panel title="Recipe 版本清單" tag={`${recipes.length} 筆`}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ background: "var(--s2)" }}>
            {HEADERS.map((header) => (
              <th key={header} style={thStyle}>
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {recipes.map((recipe) => (
            <tr key={recipe.recipeId} style={{ borderBottom: "1px solid var(--border2)" }}>
              <td style={tdStyle}>
                <div style={{ fontFamily: "monospace", color: "var(--text)" }}>
                  {recipe.recipeId}
                </div>
                <div style={{ color: "var(--text3)", fontSize: 11 }}>
                  {recipe.name} · {recipe.version}
                </div>
              </td>
              <td style={tdStyle}>
                <Chip type="approved" label={recipe.experimentItem} />
              </td>
              <td style={tdStyle}>{recipe.machineIds.join("、")}</td>
              <td style={tdStyle}>{recipe.method}</td>
              <td style={tdStyle}>
                {Object.entries(recipe.parameters)
                  .map(([key, value]) => `${key}:${value}`)
                  .join(" / ")}
              </td>
              <td style={tdStyle}>
                {recipe.updatedBy}
                <br />
                <span style={{ color: "var(--text3)", fontSize: 11 }}>{recipe.updatedAt}</span>
              </td>
            </tr>
          ))}
          {recipes.length === 0 && (
            <tr>
              <td colSpan={HEADERS.length} style={{ ...tdStyle, textAlign: "center", padding: 28 }}>
                尚無 Recipe，請先建立機台，再新增 Recipe。
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </Panel>
  );
}

const thStyle: React.CSSProperties = {
  fontSize: 10,
  letterSpacing: 1.5,
  color: "var(--text3)",
  padding: "10px 16px",
  textAlign: "left",
  fontFamily: "monospace",
  borderBottom: "1px solid var(--border2)",
};

const tdStyle: React.CSSProperties = {
  padding: "12px 16px",
  fontSize: 12.5,
  color: "var(--text2)",
  verticalAlign: "middle",
};
