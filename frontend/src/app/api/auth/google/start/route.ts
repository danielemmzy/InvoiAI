import { NextResponse } from "next/server";
import { createOAuthSecret, createPkceChallenge } from "@/lib/google-oauth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const BACKEND_API_URL = (
  process.env.BACKEND_API_URL || "http://localhost:8000"
).replace(/\/$/, "");

export async function GET(request: Request) {
  const verifier = createOAuthSecret();
  const state = createOAuthSecret();
  const challenge = createPkceChallenge(verifier);
  const callback = new URL("/api/auth/google/callback", request.url);
  const startUrl = new URL(
    "/api/v2/auth/google/start",
    BACKEND_API_URL,
  );
  startUrl.searchParams.set("redirect_uri", callback.toString());
  startUrl.searchParams.set("state", state);
  startUrl.searchParams.set("code_challenge", challenge);

  try {
    const upstream = await fetch(startUrl, {
      redirect: "manual",
      cache: "no-store",
    });
    const location = upstream.headers.get("location");
    if (!location || upstream.status < 300 || upstream.status >= 400) {
      return NextResponse.redirect(new URL("/login?reason=google-unavailable", request.url));
    }

    const response = NextResponse.redirect(location);
    const secure = process.env.NODE_ENV === "production";
    for (const [name, value] of [
      ["invoiai_google_state", state],
      ["invoiai_google_verifier", verifier],
    ]) {
      response.cookies.set(name, value, {
        httpOnly: true,
        secure,
        sameSite: "lax",
        path: "/api/auth/google",
        maxAge: 600,
      });
    }
    // Supabase Auth generates and validates the upstream OAuth state and OIDC nonce.
    return response;
  } catch {
    return NextResponse.redirect(new URL("/login?reason=google-unavailable", request.url));
  }
}
