import { NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const BACKEND_API_URL = (process.env.BACKEND_API_URL || "http://localhost:8000").replace(/\/$/, "");

async function handler(request: Request, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  if (!path?.length) return NextResponse.json({ detail: "Vendor portal path is required." }, { status: 404 });
  const incoming = new URL(request.url);
  const target = `${BACKEND_API_URL}/api/public/vendor-portal/${path.map(encodeURIComponent).join("/")}${incoming.search}`;
  const headers = new Headers();
  request.headers.forEach((value, key) => {
    if (!["host", "content-length", "cookie", "connection"].includes(key.toLowerCase())) headers.set(key, value);
  });
  const body = ["GET", "HEAD"].includes(request.method) ? undefined : await request.arrayBuffer();
  const upstream = await fetch(target, { method: request.method, headers, body, cache: "no-store" });
  const responseHeaders = new Headers();
  upstream.headers.forEach((value, key) => responseHeaders.set(key, value));
  return new NextResponse(upstream.body, { status: upstream.status, statusText: upstream.statusText, headers: responseHeaders });
}

export const GET = handler;
export const POST = handler;
