import assert from "node:assert/strict";
import test from "node:test";

import { readSupplierImportSummary } from "./supplierSync.ts";

test("reads persisted supplier import counts and per-record errors", () => {
  assert.deepEqual(
    readSupplierImportSummary({
      supplier_import: {
        counts: { total: 3, imported: 2, updated: 0, skipped: 0, failed: 1 },
        errors: [
          { resource: "vendor", external_id: "C-3", error: "MappingError" },
        ],
        completed_at: "2026-11-09T10:00:00Z",
      },
    }),
    {
      counts: { total: 3, imported: 2, updated: 0, skipped: 0, failed: 1 },
      errors: [
        { resource: "vendor", external_id: "C-3", error: "MappingError" },
      ],
      completedAt: "2026-11-09T10:00:00Z",
    },
  );
});

test("ignores missing or malformed supplier import metadata", () => {
  assert.equal(readSupplierImportSummary({}), null);
  assert.equal(
    readSupplierImportSummary({ supplier_import: { counts: {} } }),
    null,
  );
});
