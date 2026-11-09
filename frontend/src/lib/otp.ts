/**
 * Pure helpers for the six-digit email verification screen.
 *
 * Kept free of React and browser APIs so the behaviour can be tested with
 * Node's built-in test runner without adding a frontend test framework.
 */

export const OTP_LENGTH = 6;

/** Keep digits only and never exceed the code length. */
export function normalizeOtpDigits(
  value: string,
  length: number = OTP_LENGTH,
): string {
  return value
    .replace(/\D/g, "")
    .slice(0, Math.max(0, length));
}

/** A complete code is exactly `length` digits. */
export function isCompleteOtp(
  value: string,
  length: number = OTP_LENGTH,
): boolean {
  return new RegExp(`^\\d{${length}}$`).test(value);
}

/**
 * Spread a pasted value across the individual boxes.
 *
 * A paste of "123 456" or "123-456" fills all six boxes; a paste shorter
 * than the code leaves the remaining boxes empty.
 */
export function distributeOtpDigits(
  value: string,
  length: number = OTP_LENGTH,
): string[] {
  const digits = normalizeOtpDigits(value, length);
  return Array.from(
    { length: Math.max(0, length) },
    (_, index) => digits[index] ?? "",
  );
}

/** Whole seconds left before `expiresAt`, never negative. */
export function otpSecondsRemaining(
  expiresAt: string | number | null | undefined,
  now: number = Date.now(),
): number {
  if (expiresAt === null || expiresAt === undefined || expiresAt === "") {
    return 0;
  }

  const end =
    typeof expiresAt === "number"
      ? expiresAt
      : Date.parse(expiresAt);

  if (!Number.isFinite(end)) {
    return 0;
  }

  return Math.max(0, Math.ceil((end - now) / 1000));
}

/** "9:05" style countdown label. */
export function formatOtpCountdown(totalSeconds: number): string {
  const safe = Math.max(0, Math.floor(totalSeconds));
  const minutes = Math.floor(safe / 60);
  const seconds = safe % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

/**
 * Read the machine-readable code the backend puts in `detail.code`
 * (`OTP_INVALID`, `OTP_LOCKED`, ...) so the screen can offer the right
 * recovery action instead of a generic error.
 */
export function otpErrorCode(error: unknown): string | null {
  const detail = (
    error as {
      response?: { data?: { detail?: unknown } };
    }
  )?.response?.data?.detail;

  if (detail && typeof detail === "object" && "code" in detail) {
    const code = (detail as { code?: unknown }).code;
    if (typeof code === "string") {
      return code;
    }
  }

  return null;
}
