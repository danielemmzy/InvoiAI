import axios, {
  AxiosError,
  AxiosInstance,
  InternalAxiosRequestConfig,
} from "axios";

const BASE_URL = "/api/bff";

const IDEMPOTENT = new Set([
  "get",
  "head",
  "options",
]);

export const client: AxiosInstance =
  axios.create({
    baseURL: BASE_URL,
    timeout: 15_000,

    // Browser -> Next.js is same-origin.
    // The only credential is the httpOnly BFF session cookie.
    withCredentials: true,

    headers: {
      Accept: "application/json",
    },
  });

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

function isAuthEndpoint(
  url: string,
): boolean {
  return /\/auth\/(login|signup|refresh|forgot-password|resend-verification|resend-otp|verify-otp|reset-password)\/?$/.test(
    url,
  );
}

const RETURN_TO_KEY = "invoiai:return-after-login";

/** Remember the current protected screen before an expired session sends the user to login. */
export function rememberPostLoginPath(): void {
  if (!isBrowser()) return;
  const { pathname, search, hash } = window.location;
  if (!pathname || pathname.startsWith("/login") || pathname.startsWith("/signup") || pathname.startsWith("/forgot-password") || pathname.startsWith("/reset-password") || pathname.startsWith("/verify-email")) return;
  if (!pathname.startsWith("/dashboard") && !pathname.startsWith("/workspace")) return;
  try { sessionStorage.setItem(RETURN_TO_KEY, `${pathname}${search}${hash}`); } catch { /* session storage may be unavailable */ }
}

/** Consume only a safe same-origin application path; never accept absolute URLs. */
export function consumePostLoginPath(): string | null {
  if (!isBrowser()) return null;
  try {
    const path = sessionStorage.getItem(RETURN_TO_KEY);
    sessionStorage.removeItem(RETURN_TO_KEY);
    if (!path || !path.startsWith("/") || path.startsWith("//") || path.startsWith("/login") || path.startsWith("/signup")) return null;
    return path;
  } catch { return null; }
}

function removeLegacyBrowserTokens(): void {
  if (!isBrowser()) {
    return;
  }

  // Remove credentials left behind by the previous architecture.
  localStorage.removeItem(
    "access_token",
  );

  localStorage.removeItem(
    "refresh_token",
  );
}

export function getErrorMessage(
  error: unknown,
  fallback =
    "Something went wrong. Please try again.",
): string {
  if (axios.isAxiosError(error)) {
    const detail =
      error.response?.data?.detail;

    if (
      typeof detail === "string" &&
      detail.trim()
    ) {
      return detail;
    }

    if (detail && typeof detail === "object") {
      const message = (detail as { message?: unknown }).message;
      if (typeof message === "string" && message.trim()) {
        return message;
      }
    }

    if (
      error.code ===
      "ECONNABORTED"
    ) {
      return "The server took too long to respond. Please try again.";
    }

    if (!error.response) {
      return "We couldn't reach InvoiAI. Check your connection and try again.";
    }

    if (
      error.response.status >=
      500
    ) {
      return "InvoiAI is temporarily unavailable. Please try again shortly.";
    }
  }

  return fallback;
}

/* ============================================================
   REQUEST
   ============================================================ */

client.interceptors.request.use(
  (
    config: InternalAxiosRequestConfig,
  ) => {
    if (!isBrowser()) {
      return config;
    }

    removeLegacyBrowserTokens();

    /*
     * IMPORTANT:
     *
     * There is deliberately NO:
     *
     * localStorage.getItem("access_token")
     *
     * and NO:
     *
     * Authorization: Bearer ...
     *
     * here.
     *
     * Next.js BFF owns authentication.
     */

    const workspaceId =
      localStorage.getItem(
        "active_workspace_id",
      );

    if (workspaceId) {
      config.headers[
        "X-Org-Id"
      ] = workspaceId;
    }

    try {
      if (
        typeof crypto !==
          "undefined" &&
        typeof crypto.randomUUID ===
          "function"
      ) {
        config.headers[
          "X-Client-Request-ID"
        ] = crypto.randomUUID();
      }
    } catch {
      // Optional tracing header.
    }

    return config;
  },
);

/* ============================================================
   RESPONSE
   ============================================================ */

client.interceptors.response.use(
  (response) => response,

  async (error: AxiosError) => {
    const original =
      error.config as
        | (InternalAxiosRequestConfig & {
            _sessionHandled?: boolean;
          })
        | undefined;

    if (
      !original ||
      !isBrowser() ||
      error.response?.status !== 401
    ) {
      return Promise.reject(
        error,
      );
    }

    /*
     * The BFF already performs token refresh server-side.
     *
     * NEVER call /auth/refresh from this interceptor.
     */
    if (
      original._sessionHandled ||
      isAuthEndpoint(
        original.url || "",
      )
    ) {
      return Promise.reject(
        error,
      );
    }

    original._sessionHandled = true;

    rememberPostLoginPath();
    clearAuthStorage();

    if (
      !window.location.pathname.startsWith(
        "/login",
      )
    ) {
      window.location.assign(
        "/login?reason=session-expired",
      );
    }

    return Promise.reject(
      error,
    );
  },
);

/* ============================================================
   CLIENT CLEANUP
   ============================================================ */

export function clearAuthStorage(): void {
  if (!isBrowser()) {
    return;
  }

  removeLegacyBrowserTokens();

  localStorage.removeItem(
    "invoiai-store",
  );

  localStorage.removeItem(
    "active_workspace_id",
  );

  /*
   * DO NOT attempt document.cookie deletion.
   *
   * invoiai_bff_session is httpOnly.
   *
   * The BFF owns deletion of that cookie.
   */
}

/* ============================================================
   RETRY
   ============================================================ */

export function shouldRetry(
  error: unknown,
): boolean {
  if (!axios.isAxiosError(error)) {
    return false;
  }

  const method =
    error.config?.method?.toLowerCase() ||
    "get";

  const status =
    error.response?.status;

  return (
    IDEMPOTENT.has(method) &&
    (!status ||
      status >= 500 ||
      status === 429)
  );
}

export default client;