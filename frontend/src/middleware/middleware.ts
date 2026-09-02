import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PROTECTED = [
  "/dashboard",
  "/workspace",
];

const SESSION_COOKIE =
  "invoiai_bff_session";

export function middleware(
  request: NextRequest,
) {
  const { pathname } =
    request.nextUrl;

  const session =
    request.cookies.get(
      SESSION_COOKIE,
    )?.value;

  const isProtected =
    PROTECTED.some((path) =>
      pathname.startsWith(path),
    );

  if (
    isProtected &&
    !session
  ) {
    return NextResponse.redirect(
      new URL(
        "/login",
        request.url,
      ),
    );
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/workspace/:path*",
  ],
};