/**
 * Cloudflare Edge Worker for Eden Training Institute and Therapy (`eden-training-institute`).
 * 1. Serves the React SPA (`./frontend/dist`) directly from Cloudflare's global edge with zero cold start.
 * 2. Proxies `/api/*` requests to the Render Django API (`https://edenlms-api.onrender.com`)
 *    so `HttpOnly` session and CSRF cookies remain same-origin (`credentials: "same-origin"`).
 */
const DEFAULT_BACKEND_ORIGIN = "https://edenlms-api.onrender.com";

export default {
  async fetch(request, env) {
    const incomingUrl = new URL(request.url);

    if (incomingUrl.pathname.startsWith("/api/")) {
      const backendOrigin = (
        env.BACKEND_ORIGIN || DEFAULT_BACKEND_ORIGIN
      ).replace(/\/+$/, "");
      const targetUrl = `${backendOrigin}${incomingUrl.pathname}${incomingUrl.search}`;

      const proxyHeaders = new Headers(request.headers);
      proxyHeaders.set("Host", new URL(backendOrigin).host);
      proxyHeaders.set("X-Forwarded-Host", incomingUrl.host);
      proxyHeaders.set("X-Forwarded-Proto", "https");

      const init = {
        method: request.method,
        headers: proxyHeaders,
        redirect: "manual",
      };

      if (request.method !== "GET" && request.method !== "HEAD") {
        init.body = await request.arrayBuffer();
      }

      const backendResponse = await fetch(targetUrl, init);
      return new Response(backendResponse.body, {
        status: backendResponse.status,
        statusText: backendResponse.statusText,
        headers: new Headers(backendResponse.headers),
      });
    }

    return env.ASSETS.fetch(request);
  },
};