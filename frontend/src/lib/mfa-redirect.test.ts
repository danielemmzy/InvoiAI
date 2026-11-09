import assert from "node:assert/strict";
import test from "node:test";

import { mfaRedirectFor } from "./mfa-redirect.ts";

test("maps only server MFA guard responses to the setup or step-up screen", () => {
  assert.equal(mfaRedirectFor({ code: "MFA_ENROLLMENT_REQUIRED" }), "/mfa?mode=enroll");
  assert.equal(mfaRedirectFor({ code: "MFA_STEP_UP_REQUIRED" }), "/mfa?step_up=1");
  assert.equal(mfaRedirectFor({ code: "EMAIL_VERIFICATION_REQUIRED" }), null);
  assert.equal(mfaRedirectFor("MFA_STEP_UP_REQUIRED"), null);
});
