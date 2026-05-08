export type ApiResponse<T> =
  | { success: true; data: T; error: null; status: number }
  | { success: false; data: null; error: string; status: number };

export interface PaginatedResponse<T> {
  success: true;
  data: T[];
  error: null;
  status: number;
  total: number;
  page: number;
  pageSize: number;
  nextCursor?: string | null;
}

// version and services are optional fields for future multi-service health aggregation
export interface HealthCheckResponse {
  status: "ok" | "degraded" | "down";
  timestamp: string;
  version?: string;
  services?: Record<string, { status: "ok" | "degraded" | "down" }>;
}
