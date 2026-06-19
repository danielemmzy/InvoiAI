"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "react-hot-toast";
import { useState } from "react";

export default function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: 1,
            refetchOnWindowFocus: false,
            staleTime: 30 * 1000,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: "#1A1916",
            color: "#FFFFFF",
            fontFamily: "'DM Sans', sans-serif",
            fontSize: "13px",
            borderRadius: "8px",
          },
          success: {
            iconTheme: { primary: "#C8922A", secondary: "#FFF" },
          },
          error: {
            iconTheme: { primary: "#E57373", secondary: "#FFF" },
          },
        }}
      />
    </QueryClientProvider>
  );
}