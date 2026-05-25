"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import KpiCard from "@/components/ui/KpiCard";
import {
  machinesApi,
  recipesApi,
  type RecipePayload,
} from "@/services/recipes-api";
import RecipeForm from "./RecipeForm";
import RecipeTable from "./RecipeTable";

export default function RecipePage() {
  const queryClient = useQueryClient();
  // Bump to remount RecipeForm so it clears after a successful create.
  const [formNonce, setFormNonce] = useState(0);

  const recipesQuery = useQuery({
    queryKey: ["recipes"],
    queryFn: recipesApi.list,
  });
  const machinesQuery = useQuery({
    queryKey: ["machines"],
    queryFn: machinesApi.list,
  });

  const recipes = useMemo(() => recipesQuery.data ?? [], [recipesQuery.data]);
  const machines = useMemo(
    () => machinesQuery.data ?? [],
    [machinesQuery.data],
  );

  const experimentItems = useMemo(
    () =>
      Array.from(
        new Set(machines.flatMap((machine) => machine.supportedItems)),
      ),
    [machines],
  );

  const create = useMutation({
    mutationFn: (payload: RecipePayload) => recipesApi.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recipes"] });
      setFormNonce((n) => n + 1);
    },
  });

  const parameterCount = useMemo(
    () =>
      recipes.reduce(
        (sum, recipe) => sum + Object.keys(recipe.parameters).length,
        0,
      ),
    [recipes],
  );

  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: 22,
        }}
      >
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800 }}>Recipe 管理</h1>
          <p
            style={{
              fontSize: 12,
              color: "var(--text3)",
              marginTop: 4,
              fontFamily: "monospace",
            }}
          >
            ROLE C · POSTGRESQL ·{" "}
            {statusLine(recipesQuery, machinesQuery, create.isError)}
          </p>
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4,1fr)",
          gap: 14,
          marginBottom: 20,
        }}
      >
        <KpiCard
          label="Recipe 數"
          value={recipes.length}
          sub="含版本與方法"
          color="var(--blue)"
          icon="📐"
        />
        <KpiCard
          label="實驗項目"
          value={experimentItems.length}
          sub="由機台支援項目彙整"
          color="var(--cyan)"
          icon="🧪"
        />
        <KpiCard
          label="可用機台"
          value={machines.length}
          sub="可被 Recipe 綁定"
          color="var(--green)"
          icon="⚙️"
        />
        <KpiCard
          label="參數範本"
          value={parameterCount}
          sub="Recipe parameters"
          color="var(--purple)"
          icon="📝"
        />
      </div>

      <div
        style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 16 }}
      >
        <RecipeForm
          key={formNonce}
          machines={machines}
          experimentItems={experimentItems}
          submitting={create.isPending}
          onSubmit={(payload) => create.mutate(payload)}
        />
        <RecipeTable recipes={recipes} />
      </div>
    </div>
  );
}

function statusLine(
  recipesQuery: { isLoading: boolean; isError: boolean },
  machinesQuery: { isLoading: boolean; isError: boolean },
  createError: boolean,
): string {
  if (recipesQuery.isLoading || machinesQuery.isLoading) return "讀取資料庫中";
  if (recipesQuery.isError || machinesQuery.isError)
    return "後端或 PostgreSQL 尚未啟動";
  if (createError)
    return "建立 Recipe 失敗，只有實驗室人員可建立，並請確認機台與 Recipe ID";
  return "已連線 PostgreSQL";
}
