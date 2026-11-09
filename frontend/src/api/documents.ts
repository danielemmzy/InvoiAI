import client from "./client";

import {
  UploadResponse,
  HistoryResponse,
  Industry,
  SheetsExportResponse,
} from "@/types";


export interface DocumentIntelligence {
  document: {
    id: string;
    document_type?: string;
    file_name?: string;
    status?: string;
    pipeline_stage?: string;
    workflow_route?: string | null;
    processing_step?: string;
    processing_message?: string;
    processing_progress?: number;
    error_message?: string | null;
    validation_warnings?: string[];
    vendor_id?: string | null;
    vendor_name?: string | null;
    total_amount?: number | string | null;
    currency?: string | null;
    ap_enabled?: boolean;
    human_review_status?: "pending" | "accepted" | "declined" | string;
    intelligence_status?: "not_requested" | "queued" | "processing" | "complete" | "failed" | string;
    capture_status?: "pending" | "processing" | "complete" | "failed" | string;
    capture_progress?: number;
    capture_error?: string | null;
    capture_overrides?: Record<string, unknown>;
    purchase_order_id?: string | null;
    gl_account_id?: string | null;
    gl_account_code?: string | null;
    gl_account_name?: string | null;
  };
  ocr: any | null;
  analysis: any | null;
  embedding: { model_used?: string; created_at?: string } | null;
  vendor: { name?: string; risk_score?: number; risk_level?: string; is_verified?: boolean; is_blocked?: boolean; total_spend?: number | string; average_spend?: number | string; invoice_count?: number; fraud_flags?: number; anomaly_count?: number; ai_summary?: string; ai_risk_explanation?: string } | null;
  vendor_embedding_ready: boolean;
  source_document?: {
    url: string;
    file_name?: string | null;
    file_type?: string | null;
    mime_type?: string | null;
    expires_in?: number;
  } | null;
  ready: boolean;
  line_items?: any[];
  structured_data?: any;
  actions: string[];
}

export interface BatchUploadFileResult {
  filename: string;
  status: "accepted" | "error";
  error?: string;
  code?: string;
  existing_document_id?: string;
  existing_file_name?: string;
  document_id?: string;
  document?: Record<string, unknown>;
}

export interface BatchUploadResponse {
  total: number;
  accepted: number;
  failed: number;
  results: BatchUploadFileResult[];
}

export const documentsApi = {
  // =========================================================
  // Single upload
  // =========================================================

  upload: async (
    file: File,
    industry: string,
    onProgress?: (
      progress: number,
    ) => void,
    documentType?: string,
    financialAccountId?: string,
    allowDuplicate = false,
  ): Promise<UploadResponse> => {
    const formData =
      new FormData();

    formData.append(
      "file",
      file,
    );

    formData.append(
      "industry",
      industry,
    );

    formData.append(
      "document_type",
      documentType ||
        "unknown",
    );

    formData.append(
      "allow_duplicate",
      String(
        allowDuplicate,
      ),
    );

    if (
      financialAccountId
    ) {
      formData.append(
        "financial_account_id",
        financialAccountId,
      );
    }

    const {
      data,
    } =
      await client.post<any>(
        "/documents",
        formData,
        {
          headers: {
            "Content-Type":
              "multipart/form-data",
          },

          onUploadProgress:
            (event) => {
              if (
                event.total
              ) {
                onProgress?.(
                  Math.round(
                    (event.loaded /
                      event.total) *
                      100,
                  ),
                );
              }
            },
        },
      );

    return {
      invoice_id:
        data.id,
      status:
        data.status,
      document_type:
        data.document_type,
      structured_data:
        data.structured_data,
      validation_warnings:
        data.validation_warnings ||
        [],
      file_name:
        data.file_name,
      industry:
        data.industry,
      pipeline_stage:
        data.pipeline_stage,
      processing_step:
        data.processing_step,
      processing_message:
        data.processing_message,
      processing_progress:
        data.processing_progress,
      error_message:
        data.error_message,
      created_at:
        data.created_at,
    };
  },

  // =========================================================
  // Get document
  // =========================================================

  getById: async (
    invoiceId: string,
  ): Promise<UploadResponse> => {
    const {
      data,
    } =
      await client.get<any>(
        `/documents/${invoiceId}`,
      );

    return {
      invoice_id:
        data.id,
      status:
        data.status,
      document_type:
        data.document_type,
      structured_data:
        data.structured_data,
      validation_warnings:
        data.validation_warnings ||
        [],
      file_name:
        data.file_name,
      industry:
        data.industry,
      pipeline_stage:
        data.pipeline_stage,
      error_message:
        data.error_message,
      created_at:
        data.created_at,
    };
  },

  review: async (documentId: string, decision: "approve" | "reject") => {
    return (await client.post(`/documents/${documentId}/review`, null, { params: { decision } })).data;
  },

  analyze: async (documentId: string) => {
    return (await client.post(`/documents/${documentId}/analyze`)).data;
  },

  runOCR: async (documentId: string) => {
    return (await client.post(`/documents/${documentId}/ocr`)).data;
  },

  retryProcessing: async (documentId: string) => {
    return (await client.post(`/documents/${documentId}/retry-processing`)).data;
  },

  getIntelligence: async (
    documentId: string,
  ): Promise<DocumentIntelligence> => {
    const { data } = await client.get<DocumentIntelligence>(
      `/documents/${documentId}/intelligence`,
    );
    return data;
  },

  updateCapture: async (documentId: string, payload: Record<string, unknown>) => {
    const { data } = await client.patch(`/documents/${documentId}/capture`, payload);
    return data;
  },

  getCaptureOptions: async (documentId: string, field: string, q = "") => {
    const { data } = await client.get(`/documents/${documentId}/capture-options`, { params: { field, q } });
    return data as { field: string; options: Array<{ value: string; label: string; source: string; id?: string; code?: string }> };
  },

  // =========================================================
  // Batch upload
  // =========================================================

  uploadBatch: async (
    files: File[],
    industry: string,
    onProgress?: (
      progress: number,
    ) => void,
    allowDuplicate = false,
  ): Promise<BatchUploadResponse> => {
    const formData =
      new FormData();

    files.forEach(
      (file) => {
        formData.append(
          "files",
          file,
        );
      },
    );

    formData.append(
      "industry",
      industry,
    );

    formData.append(
      "document_type",
      "unknown",
    );

    formData.append(
      "allow_duplicate",
      String(
        allowDuplicate,
      ),
    );

    const {
      data,
    } =
      await client.post<BatchUploadResponse>(
        "/documents/batch",
        formData,
        {
          headers: {
            "Content-Type":
              "multipart/form-data",
          },

          onUploadProgress:
            (event) => {
              if (
                event.total
              ) {
                onProgress?.(
                  Math.round(
                    (event.loaded /
                      event.total) *
                      100,
                  ),
                );
              }
            },
        },
      );

    return data;
  },

  // =========================================================
  // History
  // =========================================================

  getHistory: async (
    offset = 0,
    limit = 20,
    industry?: string,
    query?: string,
  ): Promise<HistoryResponse> => {
    const params: Record<
      string,
      unknown
    > = {
      offset,
      limit,
    };

    if (industry) {
      params.industry =
        industry;
    }
    if (query) {
      params.query = query;
    }

    const {
      data,
      headers,
    } =
      await client.get<
        Array<
          Record<
            string,
            unknown
          >
        >
      >(
        "/documents",
        {
          params,
        },
      );

    const filtered =
      industry
        ? data.filter(
            (item) =>
              item.industry ===
              industry,
          )
        : data;

    return {
      documents:
        filtered.map(
          (
            item: Record<
              string,
              any
            >,
          ) => ({
            id: item.id,
            file_name:
              item.file_name,
            file_type:
              item.file_type,
            industry:
              item.industry,
            document_type:
              item.document_type,
            status:
              item.status,
            pipeline_stage:
              item.pipeline_stage,
            processing_step:
              item.processing_step,
            processing_message:
              item.processing_message,
            processing_progress:
              item.processing_progress,
            error_message:
              item.error_message,
            validation_warnings:
              item.validation_warnings ||
              [],
            created_at:
              item.created_at,
            sheets_url:
              item.sheets_url,
            vendor_name: item.vendor_name,
            document_number: item.document_number,
            document_date: item.document_date,
            due_date: item.due_date,
            currency: item.currency,
            subtotal: item.subtotal,
            total_amount: item.total_amount,
            amount_due: item.amount_due,
            total_quantity: item.total_quantity,
            line_item_count: item.line_item_count,
            account_id: item.account_id,
            account_code: item.account_code,
            account_name: item.account_name,
            classification_confidence: item.classification_confidence,
            human_review_status: item.human_review_status,
            intelligence_status: item.intelligence_status,
            capture_status: item.capture_status,
            capture_progress: item.capture_progress,
            capture_error: item.capture_error,
          }),
        ),

      count: Number(headers["x-total-count"] ?? filtered.length),
      offset,
      limit,
    };
  },

  // =========================================================
  // Delete
  // =========================================================

  delete: async (
    invoiceId: string,
  ): Promise<void> => {
    await client.delete(
      `/documents/${invoiceId}`,
    );
  },

  // =========================================================
  // Industries
  // =========================================================

  getIndustries:
    async (): Promise<{
      industries: Industry[];
    }> => {
      const {
        data,
      } =
        await client.get<{
          industries: Industry[];
        }>(
          "/industries",
        );

      return data;
    },
};

// ===========================================================
// Exports
// ===========================================================

export const exportApi = {
  downloadExcel:
    async (
      invoiceId: string,
    ): Promise<void> => {
      const response =
        await client.get(
          `/export/${invoiceId}/excel`,
          {
            responseType:
              "blob",
          },
        );

      const url =
        window.URL.createObjectURL(
          new Blob([
            response.data,
          ]),
        );

      const link =
        document.createElement(
          "a",
        );

      link.href = url;

      link.setAttribute(
        "download",
        `invoiai_${invoiceId.slice(
          0,
          8,
        )}.xlsx`,
      );

      document.body.appendChild(
        link,
      );

      link.click();
      link.remove();

      window.URL.revokeObjectURL(
        url,
      );
    },

  downloadCsv:
    async (
      invoiceId: string,
    ): Promise<void> => {
      const response =
        await client.get(
          `/export/${invoiceId}/csv`,
          {
            responseType:
              "blob",
          },
        );

      const url =
        window.URL.createObjectURL(
          new Blob([
            response.data,
          ]),
        );

      const link =
        document.createElement(
          "a",
        );

      link.href = url;

      link.setAttribute(
        "download",
        `invoiai_${invoiceId.slice(
          0,
          8,
        )}.csv`,
      );

      document.body.appendChild(
        link,
      );

      link.click();
      link.remove();

      window.URL.revokeObjectURL(
        url,
      );
    },

  exportToSheets:
    async (
      invoiceId: string,
    ): Promise<SheetsExportResponse> => {
      const {
        data,
      } =
        await client.post<any>(
          `/export/${invoiceId}/sheets`,
        );

      return {
        sheets_url:
          data.sheets_url ||
          data.url,
        message:
          data.message ||
          "Spreadsheet created",
      };
    },
};
