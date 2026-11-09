export type SupplierImportSummary = {
  counts: {
    total: number;
    imported: number;
    updated: number;
    skipped: number;
    failed: number;
  };
  errors: { resource: string; external_id: string | null; error: string }[];
  completedAt: string;
};

export function readSupplierImportSummary(
  metadata: unknown,
): SupplierImportSummary | null {
  if (!metadata || typeof metadata !== "object") return null;
  const summary = (metadata as Record<string, unknown>).supplier_import;
  if (!summary || typeof summary !== "object") return null;
  const value = summary as Record<string, unknown>;
  const counts = value.counts as Record<string, unknown> | undefined;
  const keys = ["total", "imported", "updated", "skipped", "failed"] as const;
  if (!counts || !keys.every((key) => Number.isInteger(counts[key])))
    return null;
  if (typeof value.completed_at !== "string" || !Array.isArray(value.errors))
    return null;
  const errors = value.errors.filter(
    (item): item is SupplierImportSummary["errors"][number] =>
      !!item &&
      typeof item === "object" &&
      typeof (item as Record<string, unknown>).resource === "string" &&
      typeof (item as Record<string, unknown>).error === "string" &&
      ((item as Record<string, unknown>).external_id === null ||
        typeof (item as Record<string, unknown>).external_id === "string"),
  );
  return {
    counts: Object.fromEntries(
      keys.map((key) => [key, counts[key]]),
    ) as SupplierImportSummary["counts"],
    errors,
    completedAt: value.completed_at,
  };
}
