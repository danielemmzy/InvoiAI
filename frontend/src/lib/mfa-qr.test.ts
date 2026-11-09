import assert from "node:assert/strict";
import test from "node:test";

import { mfaQrImageSource } from "./mfa-qr.ts";

test("keeps Supabase's SVG data URI intact for the authenticator QR image", () => {
  const qrCode = "data:image/svg+xml;utf-8,<svg></svg>";

  assert.equal(mfaQrImageSource(qrCode), qrCode);
});

test("omits the QR image source when enrollment has no code", () => {
  assert.equal(mfaQrImageSource(null), undefined);
});
