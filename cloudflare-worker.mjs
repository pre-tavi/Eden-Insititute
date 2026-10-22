/**
 * Cloudflare Edge Worker for Eden Training Institute and Therapy (`eden-training-institute`).
 * - Intercepts `/api/*`, `/eden-instructor-backoffice/*`, `/static/*`, and `/media/*`
 *   (via `run_worker_first` in `wrangler.jsonc`) and proxies them to Render (`https://edenlms-api.onrender.com`).
 * - Uses `redirect: "manual"` and rewrites backend `Location` headers so Django Admin login
 *   redirects and `HttpOnly` session/CSRF cookies stay on the Cloudflare Worker origin.
 * - Serves all other routes from `./frontend/dist` via `env.ASSETS` with SPA fallback.
 */
const DEFAULT_BACKEND_ORIGIN = "https://edenlms-api.onrender.com";

const PROXIED_PREFIXES = [
  "/api/",
  "/eden-instructor-backoffice",
  "/static/",
  "/media/",
];

function shouldProxyToBackend(pathname) {
  return PROXIED_PREFIXES.some((prefix) => pathname.startsWith(prefix));
}

export default {
  async fetch(request, env) {
    const incomingUrl = new URL(request.url);

    if (shouldProxyToBackend(incomingUrl.pathname)) {
      const backendOrigin = (
        env.BACKEND_ORIGIN || DEFAULT_BACKEND_ORIGIN
      ).replace(/\/+$/, "");
      const backendBaseUrl = new URL(backendOrigin);
      const targetUrl = `${backendOrigin}${incomingUrl.pathname}${incomingUrl.search}`;

      const proxyHeaders = new Headers(request.headers);
      proxyHeaders.set("Host", backendBaseUrl.host);
      proxyHeaders.set("X-Forwarded-Host", incomingUrl.host);
      proxyHeaders.set("X-Forwarded-Proto", "https");

      // Rewrite Origin and Referer when hitting Django Admin / API so CSRF host checks match
      if (proxyHeaders.has("Origin")) {
        proxyHeaders.set("Origin", incomingUrl.origin);
      }
      if (proxyHeaders.has("Referer")) {
        try {
          const refUrl = new URL(proxyHeaders.get("Referer"));
          proxyHeaders.set(
            "Referer",
            `${incomingUrl.origin}${refUrl.pathname}${refUrl.search}`
          );
        } catch {
          // Keep existing Referer if malformed
        }
      }

      const init = {
        method: request.method,
        headers: proxyHeaders,
        redirect: "manual",
      };

      if (request.method !== "GET" && request.method !== "HEAD") {
        init.body = await request.arrayBuffer();
      }

      const backendResponse = await fetch(targetUrl, init);
      const responseHeaders = new Headers(backendResponse.headers);

      // Keep redirects on the Cloudflare Worker domain if Render emits an absolute Location URL
      const locationHeader = responseHeaders.get("Location");
      if (locationHeader && locationHeader.startsWith(backendOrigin)) {
        responseHeaders.set(
          "Location",
          locationHeader.slice(backendOrigin.length) || "/"
        );
      }

      return new Response(backendResponse.body, {
        status: backendResponse.status,
        statusText: backendResponse.statusText,
        headers: responseHeaders,
      });
    }

    return env.ASSETS.fetch(request);
  },
};