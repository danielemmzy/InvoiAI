import assert from "node:assert/strict";
import test from "node:test";

import {
  distributeOtpDigits,
  formatOtpCountdown,
  isCompleteOtp,
  normalizeOtpDigits,
  otpErrorCode,
  otpSecondsRemaining,
} from "./otp.ts";

test("normalizeOtpDigits keeps only digits and caps the length", () => {
  assert.equal(normalizeOtpDigits(" 12-34 56 "), "123456");
  assert.equal(normalizeOtpDigits("12345678"), "123456");
  assert.equal(normalizeOtpDigits("abc"), "");
});

test("isCompleteOtp accepts exactly six digits", () => {
  assert.equal(isCompleteOtp("123456"), true);
  assert.equal(isCompleteOtp("12345"), false);
  assert.equal(isCompleteOtp("1234567"), false);
  assert.equal(isCompleteOtp("12a456"), false);
});

test("distributeOtpDigits fills boxes from a paste", () => {
  assert.deepEqual(distributeOtpDigits("123 456"), [
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
  ]);
  assert.deepEqual(distributeOtpDigits("12"), ["1", "2", "", "", "", ""]);
  assert.deepEqual(distributeOtpDigits(""), ["", "", "", "", "", ""]);
});

test("otpSecondsRemaining never goes negative", () => {
  const now = Date.parse("2026-11-09T09:00:00Z");

  assert.equal(
    otpSecondsRemaining("2026-11-09T09:10:00Z", now),
    600,
  );
  assert.equal(
    otpSecondsRemaining("2026-11-09T08:59:00Z", now),
    0,
  );
  assert.equal(otpSecondsRemaining("not-a-date", now), 0);
  assert.equal(otpSecondsRemaining(null, now), 0);
  assert.equal(otpSecondsRemaining(now + 61_000, now), 61);
});

test("formatOtpCountdown renders minutes and seconds", () => {
  assert.equal(formatOtpCountdown(600), "10:00");
  assert.equal(formatOtpCountdown(65), "1:05");
  assert.equal(formatOtpCountdown(9), "0:09");
  assert.equal(formatOtpCountdown(-3), "0:00");
});

test("otpErrorCode reads the backend detail code", () => {
  assert.equal(
    otpErrorCode({
      response: { data: { detail: { code: "OTP_LOCKED" } } },
    }),
    "OTP_LOCKED",
  );
  assert.equal(otpErrorCode({ response: { data: { detail: "nope" } } }), null);
  assert.equal(otpErrorCode(new Error("boom")), null);
});
