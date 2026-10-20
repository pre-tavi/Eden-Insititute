/**
 * Cloudflare Pages Edge Function Proxy (`/api/*` -> `https://edenlms-api.onrender.com/api/*`).
 * Why this exists:
 * 1. Allows the React SPA on Cloudflare Pages (`https://*.pages.dev`) to load in <50ms from
 *    Cloudflare's global CDN with ZERO cold start.
 * 2. Proxies `/api/*` requests at the Cloudflare edge so `HttpOnly` session cookies and
 *    CSRF tokens remain 100% first-party (`same-origin`) in all browsers (Safari, Brave, Chrome).
 */
interface Env {
  BACKEND_ORIGIN?: string;
}

export const onRequest = async (context: {
  request: Request;
  env: Env;
}): Promise<Response> => {
  const { request, env } = context;
  const incomingUrl = new URL(request.url);
  const backendOrigin = (
    env.BACKEND_ORIGIN || "https://edenlms-api.onrender.com"
  ).replace(/\/+$/, "");

  const targetUrl = `${backendOrigin}${incomingUrl.pathname}${incomingUrl.search}`;

  const proxyHeaders = new Headers(request.headers);
  proxyHeaders.set("Host", new URL(backendOrigin).host);
  proxyHeaders.set("X-Forwarded-Host", incomingUrl.host);
  proxyHeaders.set("X-Forwarded-Proto", "https");

  const init: RequestInit = {
    method: request.method,
    headers: proxyHeaders,
    redirect: "manual",
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.arrayBuffer();
  }

  const backendResponse = await fetch(targetUrl, init);
  const responseHeaders = new Headers(backendResponse.headers);

  return new Response(backendResponse.body, {
    status: backendResponse.status,
    statusText: backendResponse.statusText,
    headers: responseHeaders,
  });
};