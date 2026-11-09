"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Suspense,
  useEffect,
  useRef,
  useState,
} from "react";
import type {
  ChangeEvent,
  ClipboardEvent,
  FormEvent,
  KeyboardEvent,
} from "react";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Loader2,
  Mail,
  RefreshCw,
  ShieldCheck,
  Zap,
} from "lucide-react";
import toast from "react-hot-toast";

import { authApi } from "@/api/auth";
import { getErrorMessage } from "@/api/client";
import {
  OTP_LENGTH,
  distributeOtpDigits,
  formatOtpCountdown,
  isCompleteOtp,
  normalizeOtpDigits,
  otpErrorCode,
  otpSecondsRemaining,
} from "@/lib/otp";

const OTP_TTL_SECONDS = 10 * 60;
const RESEND_COOLDOWN_SECONDS = 60;

const EMPTY_DIGITS = Array.from(
  { length: OTP_LENGTH },
  () => "",
);

/**
 * Clock read kept outside the component so the React Compiler purity
 * rule does not mistake event-handler timing for render work.
 */
function currentTimeMs(): number {
  return Date.now();
}

type NoticeTone = "info" | "error" | "success";

function VerifyEmailContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const emailFromSignup = searchParams.get("email") || "";

  const [email, setEmail] = useState(emailFromSignup);
  const [digits, setDigits] = useState<string[]>(EMPTY_DIGITS);
  const [busy, setBusy] = useState(false);
  const [resendBusy, setResendBusy] = useState(false);
  const [secondsLeft, setSecondsLeft] = useState(OTP_TTL_SECONDS);
  const [cooldownLeft, setCooldownLeft] = useState(
    RESEND_COOLDOWN_SECONDS,
  );
  const [message, setMessage] = useState("");
  const [tone, setTone] = useState<NoticeTone>("info");

  const inputRefs = useRef<Array<HTMLInputElement | null>>([]);
  const expiresAtRef = useRef(0);
  const cooldownUntilRef = useRef(0);

  const code = digits.join("");
  const complete = isCompleteOtp(code);
  const expired = secondsLeft <= 0;

  /*
   * `emailFromSignup` seeds the address and the field only appears when
   * the query is absent, so no synchronisation effect is needed.
   */

  /*
   * One timer drives both the code expiry and the resend cooldown.
   * Timestamps live in refs so a resend can restart either window
   * without restarting the interval.
   */
  useEffect(() => {
    expiresAtRef.current =
      Date.now() + OTP_TTL_SECONDS * 1000;
    cooldownUntilRef.current =
      Date.now() + RESEND_COOLDOWN_SECONDS * 1000;

    const tick = window.setInterval(() => {
      const now = currentTimeMs();

      setSecondsLeft(
        otpSecondsRemaining(expiresAtRef.current, now),
      );
      setCooldownLeft(
        Math.max(
          0,
          Math.ceil((cooldownUntilRef.current - now) / 1000),
        ),
      );
    }, 1000);

    return () => window.clearInterval(tick);
  }, []);

  function focusBox(index: number): void {
    const clamped = Math.min(
      Math.max(index, 0),
      OTP_LENGTH - 1,
    );
    inputRefs.current[clamped]?.focus();
  }

  function restartCodeWindow(now: number): void {
    expiresAtRef.current =
      now + OTP_TTL_SECONDS * 1000;
    setSecondsLeft(OTP_TTL_SECONDS);
  }

  function startCooldown(
    now: number,
    seconds: number,
  ): void {
    cooldownUntilRef.current =
      now + Math.max(0, seconds) * 1000;
    setCooldownLeft(Math.max(0, seconds));
  }

  function handleChange(
    index: number,
    event: ChangeEvent<HTMLInputElement>,
  ): void {
    const typed = normalizeOtpDigits(event.target.value);

    if (!typed) {
      setDigits((current) =>
        current.map((digit, position) =>
          position === index ? "" : digit,
        ),
      );
      return;
    }

    const next = [...digits];

    /*
     * Autofill and IME input can deliver more than one digit to a
     * single box. Fill from the current box onward.
     */
    for (
      let offset = 0;
      offset < typed.length && index + offset < OTP_LENGTH;
      offset += 1
    ) {
      next[index + offset] = typed[offset];
    }

    setDigits(next);

    const lastWritten = Math.min(
      index + typed.length,
      OTP_LENGTH - 1,
    );
    focusBox(lastWritten);
  }

  function handleKeyDown(
    index: number,
    event: KeyboardEvent<HTMLInputElement>,
  ): void {
    if (event.key === "Backspace") {
      if (digits[index]) {
        return;
      }

      event.preventDefault();

      if (index > 0) {
        setDigits((current) =>
          current.map((digit, position) =>
            position === index - 1 ? "" : digit,
          ),
        );
        focusBox(index - 1);
      }

      return;
    }

    if (event.key === "ArrowLeft" && index > 0) {
      event.preventDefault();
      focusBox(index - 1);
    }

    if (
      event.key === "ArrowRight" &&
      index < OTP_LENGTH - 1
    ) {
      event.preventDefault();
      focusBox(index + 1);
    }
  }

  function handlePaste(
    event: ClipboardEvent<HTMLInputElement>,
  ): void {
    event.preventDefault();

    const pasted = distributeOtpDigits(
      event.clipboardData.getData("text"),
    );

    setDigits(pasted);

    const filled = pasted.filter(Boolean).length;
    focusBox(
      filled >= OTP_LENGTH ? OTP_LENGTH - 1 : filled,
    );
  }

  async function handleResendCode(): Promise<void> {
    const normalizedEmail = email.trim().toLowerCase();

    if (!normalizedEmail) {
      setTone("error");
      setMessage(
        "Enter the email address you used to sign up.",
      );
      return;
    }

    setResendBusy(true);

    try {
      const response =
        await authApi.resendOtp(normalizedEmail);

      const retryAfter =
        response.retry_after_seconds ??
        RESEND_COOLDOWN_SECONDS;

      const now = currentTimeMs();

      startCooldown(now, retryAfter);

      if (response.code_sent) {
        restartCodeWindow(now);
        setDigits(EMPTY_DIGITS);
        setTone("info");
        setMessage(
          "A new six-digit code is on its way. Older codes no longer work.",
        );
        focusBox(0);
      } else if (retryAfter > 0) {
        setTone("info");
        setMessage(
          `Please wait ${formatOtpCountdown(retryAfter)} before requesting another code.`,
        );
      } else {
        setTone("info");
        setMessage(response.message);
      }
    } catch (error) {
      setTone("error");
      setMessage(
        getErrorMessage(
          error,
          "We couldn't send a new code. Please try again.",
        ),
      );
    } finally {
      setResendBusy(false);
    }
  }

  async function handleVerifyCode(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();

    const normalizedEmail = email.trim().toLowerCase();

    if (!normalizedEmail) {
      setTone("error");
      setMessage(
        "Enter the email address you used to sign up.",
      );
      return;
    }

    if (!complete) {
      setTone("error");
      setMessage("Enter all six digits from the email.");
      focusBox(digits.findIndex((digit) => !digit));
      return;
    }

    setBusy(true);
    setMessage("");

    try {
      const response = await authApi.verifyOtp(
        normalizedEmail,
        code,
      );

      setTone("success");
      setMessage(
        response.message ||
          "Your email is verified. Taking you to sign in.",
      );
      toast.success("Email verified. Sign in to continue.");

      /*
       * Verification does not issue a session on purpose: the user
       * signs in with their password next.
       */
      router.replace("/login");
    } catch (error) {
      const errorCode = otpErrorCode(error);
      const text = getErrorMessage(
        error,
        "We couldn't verify that code. Please try again.",
      );

      setTone("error");
      setMessage(text);

      if (
        errorCode === "OTP_ALREADY_VERIFIED"
      ) {
        toast.success("Email already verified. Sign in to continue.");
        router.replace("/login");
        return;
      }

      if (
        errorCode === "OTP_INVALID" ||
        errorCode === "OTP_EXPIRED" ||
        errorCode === "OTP_LOCKED"
      ) {
        setDigits(EMPTY_DIGITS);
        focusBox(0);
      }

      /*
       * OTP_DELIVERY_FAILED keeps the same code usable, so leave the
       * boxes filled and let the user retry.
       */
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="verify-page">
      {/* ======================================================
          VISUAL PANEL
          ====================================================== */}

      <aside className="verify-visual">
        <div className="verify-orb verify-orb-one" />
        <div className="verify-orb verify-orb-two" />

        <div className="verify-brand">
          <div className="verify-brand-icon">
            <Zap size={16} />
          </div>

          <span>
            Invoi<span>AI</span>
          </span>
        </div>

        <div className="verify-visual-center">
          <div className="verify-mail-art">
            <div className="verify-mail-glow" />

            <div className="verify-mail-icon">
              <Mail size={32} />
            </div>

            <div className="verify-check">
              <CheckCircle2 size={18} />
            </div>
          </div>

          <p className="verify-visual-kicker">
            ACCOUNT SECURITY
          </p>

          <h2>
            Six digits.
            <br />
            <span>Then you&apos;re in.</span>
          </h2>

          <p>
            Email verification protects your account and keeps your
            finance workspace connected to the right person.
          </p>
        </div>

        <div className="verify-visual-footer">
          <ShieldCheck size={14} />
          <span>Secure account onboarding</span>
        </div>
      </aside>

      {/* ======================================================
          FORM
          ====================================================== */}

      <main className="verify-form-panel">
        <div className="verify-card">
          <Link
            href="/signup"
            className="verify-back"
          >
            <ArrowLeft size={15} />
            Back to signup
          </Link>

          <div className="verify-icon">
            <Mail size={25} />
          </div>

          <p className="verify-eyebrow">
            Step 02 of 03
          </p>

          <h1>
            Enter your
            <br />
            <span>code.</span>
          </h1>

          <p className="verify-description">
            We emailed a six-digit verification code. Enter it
            below to confirm your address.
          </p>

          {email ? (
            <div className="verify-email-display">
              <Mail size={16} />

              <span>{email}</span>
            </div>
          ) : (
            <div className="form-group verify-email-field">
              <label
                className="form-label"
                htmlFor="verify-email"
              >
                Email address
              </label>
              <input
                id="verify-email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(event) =>
                  setEmail(event.target.value)
                }
                placeholder="you@company.com"
                className="form-input"
              />
            </div>
          )}

          <form onSubmit={handleVerifyCode} noValidate>
            <div
              className="otp-fieldset"
              role="group"
              aria-label="Six-digit verification code"
              aria-describedby="otp-expiry"
            >
              {digits.map((digit, index) => (
                <input
                  key={index}
                  ref={(element) => {
                    inputRefs.current[index] = element;
                  }}
                  value={digit}
                  onChange={(event) =>
                    handleChange(index, event)
                  }
                  onKeyDown={(event) =>
                    handleKeyDown(index, event)
                  }
                  onPaste={handlePaste}
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={1}
                  autoComplete={
                    index === 0 ? "one-time-code" : "off"
                  }
                  aria-label={`Digit ${index + 1}`}
                  className={`otp-box${tone === "error" ? " error" : ""}`}
                  autoFocus={index === 0}
                />
              ))}
            </div>

            <p
              className={`otp-expiry${expired ? " expired" : ""}`}
              id="otp-expiry"
              aria-live="polite"
            >
              {expired
                ? "This code has expired. Request a new one."
                : `Code expires in ${formatOtpCountdown(secondsLeft)}`}
            </p>

            {message && (
              <div
                className={`verify-notice ${tone}`}
                role="status"
                aria-live="polite"
              >
                {tone === "error" ? (
                  <AlertCircle size={16} />
                ) : (
                  <CheckCircle2 size={16} />
                )}
                <span>{message}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={busy || !complete || !email.trim()}
              className="form-submit otp-submit"
            >
              {busy ? (
                <>
                  <Loader2
                    size={15}
                    className="animate-spin"
                  />
                  Verifying...
                </>
              ) : (
                "Verify email"
              )}
            </button>
          </form>

          <div className="verify-resend">
            <div>
              <strong>Didn&apos;t receive the code?</strong>

              <span>
                Check spam, then request a fresh code.
              </span>
            </div>

            <button
              type="button"
              onClick={handleResendCode}
              disabled={
                resendBusy ||
                !email.trim() ||
                cooldownLeft > 0
              }
              className="verify-resend-button"
            >
              {resendBusy ? (
                <>
                  <Loader2
                    size={15}
                    className="animate-spin"
                  />
                  Sending
                </>
              ) : cooldownLeft > 0 ? (
                <>
                  <RefreshCw size={15} />
                  Resend in{" "}
                  {formatOtpCountdown(cooldownLeft)}
                </>
              ) : (
                <>
                  <RefreshCw size={15} />
                  Resend code
                </>
              )}
            </button>
          </div>

          <Link
            href="/login"
            className="verify-login-button otp-login-link"
          >
            I&apos;ve verified my email — sign in
            <ShieldCheck size={17} />
          </Link>

          <p className="verify-footnote">
            Verification must be completed before you can access
            your finance workspace.
          </p>
        </div>
      </main>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense
      fallback={
        <div className="spinner-page">
          <Loader2 size={24} className="animate-spin" />
          <span className="spinner-label">Loading verification…</span>
        </div>
      }
    >
      <VerifyEmailContent />
    </Suspense>
  );
}
