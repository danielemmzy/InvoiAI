import test from "node:test";
import assert from "node:assert/strict";
import { countUniqueInviteSeats } from "./invitePreview.ts";

test("onboarding preview counts unique people case-insensitively, including the owner", () => {
  assert.equal(countUniqueInviteSeats(
    "Owner@company.com",
    ["reviewer@company.com", "REVIEWER@company.com", "owner@company.com"],
    "Reviewer@company.com",
  ), 2);
});
