"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[InvoiAI UI error]", error);
  }, [error]);

  return (
    <main
      style={{
        minHeight: "100svh",
        display: "grid",
        placeItems: "center",
        padding: 24,
        background: "#f4f1ea",
      }}
    >
      <section
        style={{
          maxWidth: 460,
          textAlign: "center",
          padding: 34,
          border: "1px solid #ded8cc",
          borderRadius: 20,
          background: "#fbf9f5",
          boxShadow: "10px 14px 30px rgba(30,25,18,.07)",
        }}
      >
        <div
          style={{
            width: 48,
            height: 48,
            borderRadius: 14,
            display: "grid",
            placeItems: "center",
            margin: "0 auto 18px",
            background: "#f3dddd",
            color: "#b34b45",
          }}
        >
          <AlertTriangle />
        </div>

        <h1
          style={{
            fontFamily: "Georgia, serif",
            fontSize: 30,
            margin: "0 0 8px",
          }}
        >
          Something went wrong
        </h1>

        <p
          style={{
            color: "#706c64",
            fontSize: 14,
            lineHeight: 1.6,
          }}
        >
          The page hit an unexpected problem. Your finance data is still
          protected on the server.
        </p>

        <button
          className="auth-submit"
          onClick={reset}
          style={{ marginTop: 18 }}
        >
          <RefreshCw size={15} />
          Try again
        </button>
      </section>
    </main>
  );
}