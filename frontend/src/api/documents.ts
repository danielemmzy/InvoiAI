// ─────────────────────────────────────────────
// Documents API — upload, fetch, delete
// ─────────────────────────────────────────────

import client from "./client";
import {
  UploadResponse,
  HistoryResponse,
  Industry,
  SheetsExportResponse,
} from "@/types";

export interface BatchUploadFileResult {
  filename: string;
  status: "accepted" | "error";
  error?: string;
  document?: Record<string, unknown>;
}

export interface BatchUploadResponse {
  total: number;
  accepted: number;
  failed: number;
  results: BatchUploadFileResult[];
}

export const documentsApi = {
  upload: async (file: File, industry: string, onProgress?: (progress: number) => void, documentType?: string, financialAccountId?: string): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("industry", industry);
    formData.append("document_type", documentType || "unknown");
    if (financialAccountId) formData.append("financial_account_id", financialAccountId);
    const { data } = await client.post<any>("/documents", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: (event) => {
        if (event.total) onProgress?.(Math.round((event.loaded / event.total) * 100));
      },
    });
    return {
      invoice_id: data.id,
      status: data.status,
      document_type: data.document_type,
      validation_warnings: data.validation_warnings || [],
      file_name: data.file_name,
      industry: data.industry,
      pipeline_stage: data.pipeline_stage,
      error_message: data.error_message,
      created_at: data.created_at,
    };
  },

  getById: async (invoiceId: string): Promise<UploadResponse> => {
    const { data } = await client.get<any>(`/documents/${invoiceId}`);
    return {
      invoice_id: data.id,
      status: data.status,
      document_type: data.document_type,
      validation_warnings: data.validation_warnings || [],
      file_name: data.file_name,
      industry: data.industry,
      pipeline_stage: data.pipeline_stage,
      error_message: data.error_message,
      created_at: data.created_at,
    };
  },

  // Batch upload — see routers/documents.py POST /documents/batch and
  // core/plan.py's max_batch_upload for the per-plan cap this enforces
  // server-side. This never throws on a per-file failure; check
  // result.failed / result.results for what actually happened.
  uploadBatch: async (
    files: File[],
    industry: string,
    onProgress?: (progress: number) => void
  ): Promise<BatchUploadResponse> => {
    const formData = new FormData();
    files.forEach((f) => formData.append("files", f));
    formData.append("industry", industry);
    formData.append("document_type", "unknown");
    const { data } = await client.post<BatchUploadResponse>("/documents/batch", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: (event) => {
        if (event.total) onProgress?.(Math.round((event.loaded / event.total) * 100));
      },
    });
    return data;
  },

  getHistory: async (
    offset = 0,
    limit = 20,
    industry?: string
  ): Promise<HistoryResponse> => {
    const params: Record<string, unknown> = { offset, limit };
    if (industry) params.industry = industry;
    const { data } = await client.get<Array<Record<string, unknown>>>("/documents", { params });
    const filtered = industry ? data.filter((item) => item.industry === industry) : data;
    return {
      documents: filtered.map((item: Record<string, any>) => ({
        id: item.id,
        file_name: item.file_name,
        file_type: item.file_type,
        industry: item.industry,
        document_type: item.document_type,
        status: item.status,
        validation_warnings: item.validation_warnings || [],
        created_at: item.created_at,
        sheets_url: item.sheets_url,
      })),
      count: filtered.length,
      offset,
      limit,
    };
  },

  delete: async (invoiceId: string): Promise<void> => {
    await client.delete(`/documents/${invoiceId}`);
  },

  getIndustries: async (): Promise<{ industries: Industry[] }> => {
    const { data } = await client.get<{ industries: Industry[] }>("/industries");
    return data;
  },
};

export const exportApi = {
  downloadExcel: async (invoiceId: string): Promise<void> => {
    const response = await client.get(`/export/${invoiceId}/excel`, { responseType: "blob" });
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `invoiai_${invoiceId.slice(0, 8)}.xlsx`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },

  downloadCsv: async (invoiceId: string): Promise<void> => {
    const response = await client.get(`/export/${invoiceId}/csv`, { responseType: "blob" });
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `invoiai_${invoiceId.slice(0, 8)}.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },

  exportToSheets: async (invoiceId: string): Promise<SheetsExportResponse> => {
    const { data } = await client.post<any>(`/export/${invoiceId}/sheets`);
    return {
      sheets_url: data.sheets_url || data.url,
      message: data.message || "Spreadsheet created",
    };
  },
};
