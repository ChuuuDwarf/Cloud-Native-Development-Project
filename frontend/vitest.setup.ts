import "@testing-library/jest-dom/vitest";

// Pin the API base URL for tests so assertions don't depend on a developer's
// local .env (which may point NEXT_PUBLIC_API_URL at :8001). Set before any
// test imports lib/api.ts (which reads it at module load).
process.env.NEXT_PUBLIC_API_URL = "http://localhost:8000/api";
