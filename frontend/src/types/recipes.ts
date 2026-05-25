export interface Recipe {
  recipeId: string;
  name: string;
  version: string;
  experimentItem: string;
  machineIds: string[];
  method: string;
  parameters: Record<string, string>;
  updatedBy: string;
  updatedAt: string;
}

export interface RecipePayload {
  recipeId: string;
  name: string;
  version: string;
  experimentItem: string;
  machineIds: string[];
  method: string;
  parameters: Record<string, string>;
  updatedBy: string;
}
