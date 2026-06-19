// export.ts — all export API calls
// Excel, CSV, Google Sheets

import client from "./client";
import { SheetsExportResponse } from "@/types";

export const exportApi = {
  // Download Excel — triggers browser download
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

  // Download CSV — triggers browser download
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

  // Export to Google Sheets — returns spreadsheet URL
  exportToSheets: async (invoiceId: string): Promise<SheetsExportResponse> => {
    const { data } = await client.post<SheetsExportResponse>(
      `/export/${invoiceId}/sheets`
    );
    return data;
  },
};