import { NextResponse } from "next/server";

import {
  decryptSession,
  encryptSession,
  getBffSessionCookieName,
  type BffSession,
} from "@/lib/bff-session";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const BACKEND_API_URL = (
  process.env.BACKEND_API_URL ||
  "http://localhost:8000"
).replace(/\/$/, "");

const SESSION_COOKIE = getBffSessionCookieName();

const AUTH_LOGIN_PATH = "auth/login";
const AUTH_SIGNUP_PATH = "auth/signup";
const AUTH_REFRESH_PATH = "auth/refresh";
const AUTH_LOGOUT_PATH = "auth/logout";
const RESET_PASSWORD_PATH = "auth/reset-password";

const PUBLIC_AUTH_PATHS = new Set([
  "auth/forgot-password",
  "auth/resend-verification",
]);

const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
  "host",
  "content-length",
  "cookie",
  "set-cookie",
]);

function isProduction(): boolean {
  return process.env.NODE_ENV === "production";
}

/**
 * Remove cookies from the old direct-browser -> FastAPI architecture.
 *
 * This is especially important during migration because the browser may
 * still have old access_token / refresh_token cookies.
 */
function clearLegacyCookies(
  response: NextResponse,
): void {
  response.cookies.delete("access_token");
  response.cookies.delete("refresh_token");
}

function setSessionCookie(
  response: NextResponse,
  session: BffSession,
): void {
  response.cookies.set({
    name: SESSION_COOKIE,
    value: encryptSession(session),

    httpOnly: true,

    secure: isProduction(),

    sameSite: "lax",

    path: "/",

    maxAge: 60 * 60 * 24 * 30,
  });
}

function clearSessionCookie(
  response: NextResponse,
): void {
  response.cookies.delete(SESSION_COOKIE);
}

function jsonWithoutTokens(
  data: Record<string, unknown>,
): Record<string, unknown> {
  const sanitized = {
    ...data,
  };

  delete sanitized.access_token;
  delete sanitized.refresh_token;

  return sanitized;
}

function getSession(
  request: Request,
): BffSession | null {
  const cookieHeader =
    request.headers.get("cookie") || "";

  const escapedName =
    SESSION_COOKIE.replace(
      /[.*+?^${}()|[\]\\]/g,
      "\\$&",
    );

  const match = cookieHeader.match(
    new RegExp(
      `(?:^|;\\s*)${escapedName}=([^;]*)`,
    ),
  );

  if (!match?.[1]) {
    return null;
  }

  return decryptSession(
    decodeURIComponent(match[1]),
  );
}

/**
 * Same-origin BFF requests only.
 *
 * This gives us a useful CSRF boundary because the browser no longer
 * talks directly to FastAPI.
 */
function isSameOrigin(
  request: Request,
): boolean {
  const origin =
    request.headers.get("origin");

  if (!origin) {
    return true;
  }

  return (
    origin ===
    new URL(request.url).origin
  );
}

function assertCsrfSafe(
  request: Request,
): NextResponse | null {
  if (
    ["GET", "HEAD", "OPTIONS"].includes(
      request.method,
    )
  ) {
    return null;
  }

  if (isSameOrigin(request)) {
    return null;
  }

  return NextResponse.json(
    {
      detail:
        "Cross-site requests are not allowed.",
    },
    {
      status: 403,
    },
  );
}

function buildBackendUrl(
  path: string,
  request: Request,
): string {
  const incoming =
    new URL(request.url);

  return (
    `${BACKEND_API_URL}/api/v2/${path}` +
    `${incoming.search}`
  );
}

function buildBackendHeaders(
  request: Request,
  accessToken?: string,
  allowExplicitAuthorization = false,
): Headers {
  const headers = new Headers();

  request.headers.forEach(
    (value, key) => {
      const lower =
        key.toLowerCase();

      if (
        HOP_BY_HOP_HEADERS.has(
          lower,
        )
      ) {
        return;
      }

      if (lower === "authorization") {
        return;
      }

      headers.set(key, value);
    },
  );

  /**
   * Password reset is the only endpoint where the browser may
   * intentionally provide a one-time Authorization token.
   */
  if (allowExplicitAuthorization) {
    const authorization =
      request.headers.get(
        "authorization",
      );

    if (authorization) {
      headers.set(
        "Authorization",
        authorization,
      );

      return headers;
    }
  }

  if (accessToken) {
    headers.set(
      "Authorization",
      `Bearer ${accessToken}`,
    );
  }

  return headers;
}

async function readBody(
  request: Request,
): Promise<ArrayBuffer | undefined> {
  if (
    request.method === "GET" ||
    request.method === "HEAD"
  ) {
    return undefined;
  }

  return request.arrayBuffer();
}

async function backendRequest(
  request: Request,
  path: string,
  accessToken?: string,
  body?: BodyInit,
  allowExplicitAuthorization = false,
): Promise<Response> {
  return fetch(
    buildBackendUrl(path, request),
    {
      method: request.method,

      headers: buildBackendHeaders(
        request,
        accessToken,
        allowExplicitAuthorization,
      ),

      body,

      redirect: "manual",

      cache: "no-store",
    },
  );
}

function copyResponseHeaders(
  upstream: Response,
): Headers {
  const headers = new Headers();

  upstream.headers.forEach(
    (value, key) => {
      const lower =
        key.toLowerCase();

      if (
        HOP_BY_HOP_HEADERS.has(
          lower,
        )
      ) {
        return;
      }

      /*
       * Node fetch can transparently decode compressed responses.
       * Forwarding content-encoding after that can corrupt the browser
       * response.
       */
      if (
        lower === "content-encoding"
      ) {
        return;
      }

      headers.set(key, value);
    },
  );

  return headers;
}

function forwardUpstream(
  upstream: Response,
): NextResponse {
  const location =
    upstream.headers.get(
      "location",
    );

  /**
   * Preserve backend OAuth redirects.
   */
  if (
    location &&
    upstream.status >= 300 &&
    upstream.status < 400
  ) {
    const response =
      NextResponse.redirect(
        location,
        upstream.status as
          | 301
          | 302
          | 303
          | 307
          | 308,
      );

    clearLegacyCookies(response);

    return response;
  }

  const response =
    new NextResponse(
      upstream.body,
      {
        status:
          upstream.status,

        statusText:
          upstream.statusText,

        headers:
          copyResponseHeaders(
            upstream,
          ),
      },
    );

  clearLegacyCookies(response);

  return response;
}

/* ============================================================
   LOGIN / SIGNUP
   ============================================================ */

async function handleLoginOrSignup(
  request: Request,
  path: string,
): Promise<NextResponse> {
  const upstream =
    await backendRequest(
      request,
      path,
      undefined,
      await readBody(request),
    );

  const contentType =
    upstream.headers.get(
      "content-type",
    ) || "";

  if (
    !contentType.includes(
      "application/json",
    )
  ) {
    return forwardUpstream(
      upstream,
    );
  }

  const data =
    (await upstream.json()) as Record<
      string,
      unknown
    >;

  if (!upstream.ok) {
    const response =
      NextResponse.json(
        data,
        {
          status:
            upstream.status,
        },
      );

    clearLegacyCookies(response);

    return response;
  }

  const accessToken =
    typeof data.access_token ===
    "string"
      ? data.access_token
      : null;

  const refreshToken =
    typeof data.refresh_token ===
    "string"
      ? data.refresh_token
      : null;

  const response =
    NextResponse.json(
      jsonWithoutTokens(data),
      {
        status:
          upstream.status,
      },
    );

  if (
    accessToken &&
    refreshToken
  ) {
    setSessionCookie(
      response,
      {
        accessToken,
        refreshToken,
      },
    );
  }

  clearLegacyCookies(response);

  return response;
}

/* ============================================================
   REFRESH
   ============================================================ */

async function handleRefresh(
  request: Request,
  session: BffSession | null,
): Promise<NextResponse> {
  if (!session?.refreshToken) {
    const response =
      NextResponse.json(
        {
          detail:
            "Session expired. Please log in again.",
        },
        {
          status: 401,
        },
      );

    clearSessionCookie(response);
    clearLegacyCookies(response);

    return response;
  }

  const upstream =
    await fetch(
      `${BACKEND_API_URL}/api/v2/${AUTH_REFRESH_PATH}`,
      {
        method: "POST",

        headers: {
          "Content-Type":
            "application/json",

          Accept:
            "application/json",
        },

        body: JSON.stringify({
          refresh_token:
            session.refreshToken,
        }),

        redirect: "manual",

        cache: "no-store",
      },
    );

  const data =
    (await upstream.json()) as Record<
      string,
      unknown
    >;

  if (!upstream.ok) {
    const response =
      NextResponse.json(
        data,
        {
          status:
            upstream.status,
        },
      );

    clearSessionCookie(response);
    clearLegacyCookies(response);

    return response;
  }

  const accessToken =
    typeof data.access_token ===
    "string"
      ? data.access_token
      : null;

  const refreshToken =
    typeof data.refresh_token ===
    "string"
      ? data.refresh_token
      : null;

  if (
    !accessToken ||
    !refreshToken
  ) {
    const response =
      NextResponse.json(
        {
          detail:
            "Session refresh failed.",
        },
        {
          status: 401,
        },
      );

    clearSessionCookie(response);
    clearLegacyCookies(response);

    return response;
  }

  const response =
    NextResponse.json(
      jsonWithoutTokens(data),
      {
        status:
          upstream.status,
      },
    );

  setSessionCookie(
    response,
    {
      accessToken,
      refreshToken,
    },
  );

  clearLegacyCookies(response);

  return response;
}

/* ============================================================
   LOGOUT
   ============================================================ */

async function handleLogout(
  request: Request,
  session: BffSession | null,
): Promise<NextResponse> {
  if (session?.accessToken) {
    try {
      await backendRequest(
        request,
        AUTH_LOGOUT_PATH,
        session.accessToken,
      );
    } catch {
      // Local session cleanup must still happen.
    }
  }

  const response =
    NextResponse.json({
      message:
        "Logged out successfully",
    });

  clearSessionCookie(response);
  clearLegacyCookies(response);

  return response;
}

/* ============================================================
   AUTHENTICATED PROXY
   ============================================================ */

async function proxyAuthenticatedRequest(
  request: Request,
  path: string,
  session: BffSession,
): Promise<NextResponse> {
  const body =
    await readBody(request);

  const allowExplicitAuthorization =
    path ===
    RESET_PASSWORD_PATH;

  let upstream =
    await backendRequest(
      request,
      path,
      session.accessToken,
      body,
      allowExplicitAuthorization,
    );

  /**
   * The browser does not refresh anything.
   *
   * BFF receives the 401, uses the encrypted refresh token,
   * obtains a new Supabase session, then retries the original
   * FastAPI request.
   */
  if (
    upstream.status === 401 &&
    path !== AUTH_REFRESH_PATH
  ) {
    const refreshResponse =
      await fetch(
        `${BACKEND_API_URL}/api/v2/${AUTH_REFRESH_PATH}`,
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json",

            Accept:
              "application/json",
          },

          body: JSON.stringify({
            refresh_token:
              session.refreshToken,
          }),

          redirect: "manual",

          cache: "no-store",
        },
      );

    if (refreshResponse.ok) {
      const refreshed =
        (await refreshResponse.json()) as Record<
          string,
          unknown
        >;

      const accessToken =
        typeof refreshed.access_token ===
        "string"
          ? refreshed.access_token
          : null;

      const refreshToken =
        typeof refreshed.refresh_token ===
        "string"
          ? refreshed.refresh_token
          : null;

      if (
        accessToken &&
        refreshToken
      ) {
        upstream =
          await backendRequest(
            request,
            path,
            accessToken,
            body,
            allowExplicitAuthorization,
          );

        const response =
          forwardUpstream(
            upstream,
          );

        if (
          upstream.status === 401
        ) {
          clearSessionCookie(
            response,
          );

          return response;
        }

        setSessionCookie(
          response,
          {
            accessToken,
            refreshToken,
          },
        );

        return response;
      }
    }

    const response =
      forwardUpstream(
        upstream,
      );

    clearSessionCookie(
      response,
    );

    return response;
  }

  return forwardUpstream(
    upstream,
  );
}

/* ============================================================
   MAIN BFF HANDLER
   ============================================================ */

async function handler(
  request: Request,
  context: {
    params: Promise<{
      path: string[];
    }>;
  },
): Promise<NextResponse> {
  const csrfFailure =
    assertCsrfSafe(
      request,
    );

  if (csrfFailure) {
    return csrfFailure;
  }

  const {
    path: segments,
  } = await context.params;

  const path =
    segments.join("/");

  if (!path) {
    return NextResponse.json(
      {
        detail:
          "BFF route requires a backend path.",
      },
      {
        status: 404,
      },
    );
  }

  /*
   * Login/signup establish the BFF session.
   */
  if (
    path === AUTH_LOGIN_PATH ||
    path === AUTH_SIGNUP_PATH
  ) {
    return handleLoginOrSignup(
      request,
      path,
    );
  }

  const session =
    getSession(request);

  /*
   * Explicit refresh is supported, but the browser normally never
   * needs to call this because authenticated requests automatically
   * refresh inside the BFF.
   */
  if (
    path === AUTH_REFRESH_PATH
  ) {
    return handleRefresh(
      request,
      session,
    );
  }

  if (
    path === AUTH_LOGOUT_PATH
  ) {
    return handleLogout(
      request,
      session,
    );
  }

  /*
   * Public auth endpoints.
   */
  if (
    PUBLIC_AUTH_PATHS.has(
      path,
    )
  ) {
    return forwardUpstream(
      await backendRequest(
        request,
        path,
        undefined,
        await readBody(request),
      ),
    );
  }

  /*
   * Password recovery can operate without a BFF session because the
   * reset page supplies the one-time Supabase recovery token.
   */
  if (
    !session &&
    path === RESET_PASSWORD_PATH
  ) {
    return forwardUpstream(
      await backendRequest(
        request,
        path,
        undefined,
        await readBody(request),
        true,
      ),
    );
  }

  /*
   * Every other backend API request requires a BFF session.
   */
  if (!session) {
    return NextResponse.json(
      {
        detail:
          "Authentication required",
      },
      {
        status: 401,
      },
    );
  }

  return proxyAuthenticatedRequest(
    request,
    path,
    session,
  );
}

export const GET = handler;
export const POST = handler;
export const PUT = handler;
export const PATCH = handler;
export const DELETE = handler;
export const OPTIONS = handler;