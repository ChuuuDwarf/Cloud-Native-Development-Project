import { httpClient } from "@/api/httpClient";
import type { ApiResponse, PageResponse } from "@/types/api";
export type { Recipe, RecipePayload } from "@/types/recipes";
export { machinesApi } from "@/services/machines-api";
export type { Machine } from "@/types/machines";
import type { Recipe, RecipePayload } from "@/types/recipes";

export const recipesApi = {
  async list(): Promise<Recipe[]> {
    const res = await httpClient.get<PageResponse<Recipe>>("/recipes");
    return res.data.items;
  },

  async create(payload: RecipePayload): Promise<Recipe> {
    const res = await httpClient.post<ApiResponse<Recipe>>("/recipes", payload);
    return res.data.data;
  },

  async update(recipeId: string, payload: RecipePayload): Promise<Recipe> {
    const res = await httpClient.patch<ApiResponse<Recipe>>(`/recipes/${recipeId}`, payload);
    return res.data.data;
  },
};
