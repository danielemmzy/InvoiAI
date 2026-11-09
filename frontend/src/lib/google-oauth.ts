import { createHash, randomBytes, timingSafeEqual } from "node:crypto";

export function createOAuthSecret(): string {
  return randomBytes(32).toString("base64url");
}

export function createPkceChallenge(verifier: string): string {
  return createHash("sha256").update(verifier).digest("base64url");
}

export function matchesOAuthState(value: string, expected: string): boolean {
  if (!value || value.length !== expected.length) return false;
  return timingSafeEqual(Buffer.from(value), Buffer.from(expected));
}
