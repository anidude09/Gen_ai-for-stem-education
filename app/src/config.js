/**
 * config.js
 *
 * Centralized application configuration.
 *
 * In development (npm run dev): API calls go to http://localhost:8001
 * In production (built & served by FastAPI): API calls use relative URLs
 * (same-origin), so API_BASE_URL is empty.
 */

export const API_BASE_URL =
    import.meta.env.DEV ? "http://localhost:8001" : "";
