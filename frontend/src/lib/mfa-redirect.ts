export function mfaRedirectFor(detail: unknown): string | null {
  if (!detail || typeof detail !== "object" || !("code" in detail)) return null;
  const code = (detail as { code?: unknown }).code;
  if (code === "MFA_ENROLLMENT_REQUIRED") return "/mfa?mode=enroll";
  if (code === "MFA_STEP_UP_REQUIRED") return "/mfa?step_up=1";
  return null;
}
