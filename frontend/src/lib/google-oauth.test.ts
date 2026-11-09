import assert from "node:assert/strict";
import test from "node:test";

import { matchesOAuthState } from "./google-oauth.ts";

test("matches OAuth callback state only to the originating state", () => {
  assert.equal(matchesOAuthState("state-value", "state-value"), true);
  assert.equal(matchesOAuthState("attacker-value", "state-value"), false);
  assert.equal(matchesOAuthState("", "state-value"), false);
  assert.equal(matchesOAuthState("state-value", ""), false);
});
