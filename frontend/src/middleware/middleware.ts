import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Routes that require login
const PROTECTED = ["/dashboard"];
// Routes only for logged-out users
const AUTH_ONLY = ["/login", "/signup"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Check for token in cookies (we'll set this on login)
  const token = request.cookies.get("access_token")?.value;

  const isProtected = PROTECTED.some((p) => pathname.startsWith(p));
  const isAuthOnly = AUTH_ONLY.some((p) => pathname.startsWith(p));

  // Redirect to login if trying to access dashboard without token
  if (isProtected && !token) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  // Redirect to dashboard if already logged in and trying to access login/signup
  if (isAuthOnly && token) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*", "/login", "/signup"],
};