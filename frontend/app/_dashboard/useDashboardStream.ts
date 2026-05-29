import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";

/**
 * Subscribe to ``GET /api/dashboard/stream`` (SSE). On any event, invalidate
 * the ``["dashboard"]`` query so the next render re-fetches. The handler
 * intentionally ignores event names — every event means "something changed,
 * re-pull the snapshot."
 *
 * Falls back silently if ``EventSource`` is unavailable or the connection
 * fails. The parent ``useQuery`` polls every 30s, which covers freshness
 * even when the SSE channel is down.
 */
export function useDashboardStream(): void {
  const qc = useQueryClient();
  useEffect(() => {
    if (typeof window === "undefined" || typeof EventSource === "undefined") return;

    // Match the fallback baseURL used in src/services/httpClient.ts so the
    // EventSource hits the backend (8000) and not the Next dev server (3000)
    // when NEXT_PUBLIC_API_URL isn't set — otherwise SSE silently 404s and
    // the dashboard falls back to 30s polling.
    const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";
    const url = `${base}/dashboard/stream`;

    let es: EventSource | null = null;
    const invalidate = () => {
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    };

    try {
      es = new EventSource(url, { withCredentials: true });
      // Backend emits named "dashboard" events; keep onmessage as a defensive
      // fallback in case the server ever sends an unnamed default event.
      es.addEventListener("dashboard", invalidate);
      es.onmessage = invalidate;
      es.onerror = () => {
        // EventSource auto-reconnects with backoff; if it can't, the 30s
        // polling on the parent useQuery still keeps the UI fresh.
      };
    } catch {
      // ignore — polling fallback covers freshness
    }

    return () => {
      es?.close();
    };
  }, [qc]);
}
