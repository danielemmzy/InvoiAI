import assert from "node:assert/strict";
import test from "node:test";

import { describeUploadRejection } from "./uploadErrors.ts";

test("describes unsupported and oversized files in plain language", () => {
  assert.equal(
    describeUploadRejection([{ code: "file-invalid-type" }]),
    "Choose a PDF, JPG, PNG, or WEBP file.",
  );
  assert.equal(
    describeUploadRejection([{ code: "file-too-large" }]),
    "This file is larger than the 10 MB limit.",
  );
});

test("explains batch limit errors and gives a useful fallback", () => {
  assert.equal(
    describeUploadRejection([{ code: "too-many-files" }]),
    "You can upload fewer files at a time on your current plan.",
  );
  assert.equal(
    describeUploadRejection([{ code: "unknown" }]),
    "This file could not be added. Check the file and try again.",
  );
});
