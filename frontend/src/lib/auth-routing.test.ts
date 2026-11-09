import assert from "node:assert/strict";
import test from "node:test";

import { authLandingPath } from "./auth-routing.ts";

test("routes administrators through MFA before selecting a workspace", () => {
  assert.equal(authLandingPath(true, false, false), "/mfa?mode=enroll");
  assert.equal(authLandingPath(false, true, false), "/mfa?step_up=1");
});

test("sends first-time Google users to onboarding and existing users to the dashboard", () => {
  assert.equal(authLandingPath(false, false, false), "/onboarding");
  assert.equal(authLandingPath(false, false, true), "/dashboard");
});
