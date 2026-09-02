import { client } from "./client";

export type PurchaseOrderStatus = "open" | "partially_matched" | "matched";

export interface PurchaseOrderRow {
  id: string;
  po_number: string;
  vendor_id: string;
  vendor_name: string;
  amount: number;
  matched_amount: number;
  currency: string;
  is_open: boolean;
  issued_date: string | null;
  expiry_date: string | null;
  status: PurchaseOrderStatus;
}

export interface PurchaseOrderList {
  items: PurchaseOrderRow[];
  total: number;
  limit: number;
  offset: number;
}

export interface PurchaseOrderFilters {
  vendor_id?: string;
  is_open?: boolean;
  search?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
}

function toQuery(filters?: PurchaseOrderFilters) {
  if (!filters) return "";
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") params.set(k, String(v));
  });
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

// See BACKEND_INTEGRATION_AP_DASHBOARD.md §10 — this router does not exist
// on the backend yet. The PurchaseOrderService and repository underneath it
// already do; this module is written against the spec so the frontend and
// backend meet in the middle once it's added.
export const purchaseOrdersApi = {
  list: async (filters?: PurchaseOrderFilters) =>
    (await client.get<PurchaseOrderList>(`/purchase-orders${toQuery(filters)}`)).data,
  get: async (id: string) => (await client.get<PurchaseOrderRow>(`/purchase-orders/${id}`)).data,
  create: async (input: Partial<PurchaseOrderRow>) =>
    (await client.post<PurchaseOrderRow>("/purchase-orders", input)).data,
};
