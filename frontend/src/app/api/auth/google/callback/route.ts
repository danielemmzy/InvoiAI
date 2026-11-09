import { NextRequest, NextResponse } from "next/server";
import { matchesOAuthState } from "@/lib/google-oauth";
import {
  encryptSession,
  getBffSessionCookieName,
} from "@/lib/bff-session";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const BACKEND_API_URL = (
  process.env.BACKEND_API_URL || "http://localhost:8000"
).replace(/\/$/, "");
const GOOGLE_COOKIES = [
  "invoiai_google_state",
  "invoiai_google_verifier",
];

function finish(request: NextRequest, destination: string) {
  const response = NextResponse.redirect(new URL(destination, request.url));
  for (const name of GOOGLE_COOKIES) response.cookies.delete(name);
  return response;
}

export async function GET(request: NextRequest) {
  const providerError = request.nextUrl.searchParams.get("error");
  if (providerError) {
    const reason = providerError === "access_denied"
      ? "google-cancelled"
      : "google-failed";
    return finish(request, `/login?reason=${reason}`);
  }

  const state = request.nextUrl.searchParams.get("state") || "";
  const expectedState = request.cookies.get("invoiai_google_state")?.value || "";
  const verifier = request.cookies.get("invoiai_google_verifier")?.value;
  const stateMatches = matchesOAuthState(state, expectedState);

  if (!stateMatches || !verifier) {
    return finish(request, "/login?reason=google-failed");
  }

  const code = request.nextUrl.searchParams.get("code");
  if (!code || code.length > 4096) {
    return finish(request, "/login?reason=google-failed");
  }

  try {
    const upstream = await fetch(
      `${BACKEND_API_URL}/api/v2/auth/google/exchange`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ code, code_verifier: verifier }),
        cache: "no-store",
      },
    );
    if (!upstream.ok) {
      return finish(request, "/login?reason=google-failed");
    }

    const auth = await upstream.json() as {
      access_token?: unknown;
      refresh_token?: unknown;
      mfa_enrollment_required?: unknown;
      mfa_challenge_required?: unknown;
    };
    if (
      typeof auth.access_token !== "string" ||
      typeof auth.refresh_token !== "string"
    ) {
      return finish(request, "/login?reason=google-failed");
    }

    const destination = auth.mfa_enrollment_required === true
      ? "/mfa?mode=enroll"
      : auth.mfa_challenge_required === true
        ? "/mfa?step_up=1"
        : "/dashboard";
    const response = finish(request, destination);
    response.cookies.set(getBffSessionCookieName(), encryptSession({
      accessToken: auth.access_token,
      refreshToken: auth.refresh_token,
    }), {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 60 * 60 * 24 * 30,
    });
    response.cookies.delete("access_token");
    response.cookies.delete("refresh_token");
    return response;
  } catch {
    return finish(request, "/login?reason=google-failed");
  }
}
