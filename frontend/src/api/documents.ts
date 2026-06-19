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

export const documentsApi = {
  // Upload a file — multipart/form-data
  // industry comes from the dropdown
  upload: async (file: File, industry: string): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("industry", industry);

    const { data } = await client.post<UploadResponse>("/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
  },

  // Get a single document result by ID
  getById: async (invoiceId: string): Promise<UploadResponse> => {
    const { data } = await client.get<UploadResponse>(`/invoice/${invoiceId}`);
    return data;
  },

  // Get paginated document history
  getHistory: async (
    offset = 0,
    limit = 20,
    industry?: string
  ): Promise<HistoryResponse> => {
    const params: Record<string, unknown> = { offset, limit };
    if (industry) params.industry = industry;

    const { data } = await client.get<HistoryResponse>("/history", { params });
    return data;
  },

  // Delete a document
  delete: async (invoiceId: string): Promise<void> => {
    await client.delete(`/invoice/${invoiceId}`);
  },

  // Get all supported industries for the dropdown
  getIndustries: async (): Promise<{ industries: Industry[] }> => {
    const { data } = await client.get<{ industries: Industry[] }>("/industries");
    return data;
  },
};

export const exportApi = {
  // Download Excel — returns a blob URL
  downloadExcel: async (invoiceId: string): Promise<void> => {
    const response = await client.get(`/export/${invoiceId}/excel`, {
      responseType: "blob",
    });
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `invoiai_${invoiceId.slice(0, 8)}.xlsx`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },

  // Download CSV
  downloadCsv: async (invoiceId: string): Promise<void> => {
    const response = await client.get(`/export/${invoiceId}/csv`, {
      responseType: "blob",
    });
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `invoiai_${invoiceId.slice(0, 8)}.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },

  // Export to Google Sheets — returns URL
  exportToSheets: async (invoiceId: string): Promise<SheetsExportResponse> => {
    const { data } = await client.post<SheetsExportResponse>(
      `/export/${invoiceId}/sheets`
    );
    return data;
  },
};