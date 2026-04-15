/**
 * Backend base URL for server-side proxy routes.
 * Use a dynamic env key so Next.js does not inline a build-time value into the bundle
 * (Docker/Cloud Run set BACKEND_URL when the container starts).
 */
export function getBackendUrl(): string {
  const key = "BACKEND" + "_URL";
  const raw = process.env[key];
  if (typeof raw === "string" && raw.length > 0) {
    return raw.replace(/\/$/, "");
  }
  return "http://localhost:8000";
}
