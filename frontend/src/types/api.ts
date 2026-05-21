// Mirrors backend app/common/schemas/responses.py.
// Every endpoint returns one of these envelopes.

export interface ApiResponse<T> {
  data: T;
  message: string;
}

export interface PageResponse<T> {
  items: T[];
  page: number;
  pageSize: number;
  total: number;
}

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}
