"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, CornerUpLeft } from "lucide-react";

type Destination = { href: string; label: string; explicit: boolean };
const ROUTE_MAP_KEY = "invoiai:navigation:route-map:v1";

function labelForPath(path: string): string {
  const pathname = path.split("?")[0].replace(/\/$/, "") || "/dashboard";
  const exact: Record<string, string> = {
    "/dashboard": "Overview",
    "/dashboard/history": "Documents",
    "/dashboard/upload": "Receive document",
    "/dashboard/ap": "AP Control Center",
    "/dashboard/ap/exceptions": "AP exceptions",
    "/dashboard/ap/aging": "AP aging",
    "/dashboard/ap/payments": "AP payments",
    "/dashboard/approvals": "Approvals",
    "/dashboard/purchase-orders": "Purchase Orders",
    "/dashboard/vendors": "Vendors",
    "/dashboard/insights": "Insights",
    "/dashboard/billing": "Billing",
    "/dashboard/settings": "Settings",
    "/dashboard/personal": "Personal Finance",
    "/integrations": "Integrations",
  };
  if (exact[pathname]) return exact[pathname];
  if (/\/dashboard\/document\/[^/]+\/ap-processing$/.test(pathname)) return "AP processing";
  if (/\/dashboard\/document\/[^/]+$/.test(pathname)) return "Document Intelligence";
  if (/\/dashboard\/vendors\/[^/]+$/.test(pathname)) return "Vendor details";
  if (pathname.startsWith("/dashboard/settings/")) return "Settings";
  if (pathname.startsWith("/dashboard/personal/")) {
    const last = pathname.split("/").pop() || "Personal Finance";
    return last.split("-").map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(" ");
  }
  const last = pathname.split("/").filter(Boolean).pop() || "previous page";
  return last.split("-").map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(" ");
}

function fallbackForPath(path: string): Destination {
  const pathname = path.split("?")[0].replace(/\/$/, "") || "/dashboard";
  if (/\/dashboard\/document\/[^/]+\/ap-processing$/.test(pathname)) {
    return { href: pathname.replace(/\/ap-processing$/, ""), label: "Document Intelligence", explicit: false };
  }
  if (/\/dashboard\/document\/[^/]+$/.test(pathname)) return { href: "/dashboard/history", label: "Documents", explicit: false };
  if (/\/dashboard\/vendors\/[^/]+$/.test(pathname)) return { href: "/dashboard/vendors", label: "Vendors", explicit: false };
  if (pathname.startsWith("/dashboard/settings/")) return { href: "/dashboard/settings", label: "Settings", explicit: false };
  if (pathname.startsWith("/dashboard/personal/")) return { href: "/dashboard/personal", label: "Personal Finance", explicit: false };
  if (pathname === "/dashboard/ap/exceptions" || pathname.startsWith("/dashboard/ap/")) return { href: "/dashboard/ap", label: "AP Control Center", explicit: false };
  if (pathname === "/dashboard") return { href: "/dashboard/history", label: "Documents", explicit: false };
  if (pathname === "/integrations") return { href: "/dashboard/settings", label: "Settings", explicit: false };
  const parent = pathname.slice(0, pathname.lastIndexOf("/"));
  if (parent.startsWith("/dashboard/") && parent !== "/dashboard") return { href: parent, label: labelForPath(parent), explicit: false };
  return { href: "/dashboard", label: "Overview", explicit: false };
}

/**
 * Shared app-wide dashboard back control. It is mounted by DashboardLayout,
 * so pages get the same behavior without having to add a button individually.
 */
export default function ContextualBackButton() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const searchKey = searchParams.toString();
  const router = useRouter();
  const [destination, setDestination] = useState<Destination>(() => fallbackForPath("/dashboard"));
  const [canGoBack, setCanGoBack] = useState(false);

  useEffect(() => {
    const current = `${window.location.pathname}${window.location.search}`;
    const params = new URLSearchParams(window.location.search);
    const requested = params.get("returnTo") || "";
    const safeInternalPath = (requested === "/dashboard" || requested.startsWith("/dashboard/") || requested.startsWith("/integrations")) && !requested.startsWith("//") && !requested.includes("\\") && !requested.includes(":");
    if (safeInternalPath) {
      const requestedLabel = params.get("returnLabel") || labelForPath(requested);
      setDestination({ href: requested, label: requestedLabel, explicit: true });
    } else {
      const historyIndex = window.history.state?.idx;
      let routeMap: Record<string, string> = {};
      try {
        routeMap = JSON.parse(window.sessionStorage.getItem(ROUTE_MAP_KEY) || "{}");
      } catch { routeMap = {}; }
      const previous = typeof historyIndex === "number" && historyIndex > 0 ? routeMap[String(historyIndex - 1)] || "" : "";
      const validPrevious = previous.startsWith("/dashboard") || previous.startsWith("/integrations");
      if (typeof historyIndex === "number" && historyIndex > 0 && validPrevious && previous !== current) {
        setDestination({ href: previous, label: labelForPath(previous), explicit: false });
        setCanGoBack(true);
      } else {
        setDestination(fallbackForPath(current));
        setCanGoBack(false);
      }
    }
    const historyIndex = window.history.state?.idx;
    if (typeof historyIndex === "number") {
      let routeMap: Record<string, string> = {};
      try { routeMap = JSON.parse(window.sessionStorage.getItem(ROUTE_MAP_KEY) || "{}"); } catch { routeMap = {}; }
      // Drop forward entries when the user navigates to a new page from history.
      for (const key of Object.keys(routeMap)) if (Number(key) > historyIndex) delete routeMap[key];
      routeMap[String(historyIndex)] = current;
      try { window.sessionStorage.setItem(ROUTE_MAP_KEY, JSON.stringify(routeMap)); } catch { /* storage may be unavailable */ }
    }
  }, [pathname, searchKey]);

  function goBack() {
    if (destination.explicit) {
      router.push(destination.href);
      return;
    }
    const hasNextHistoryEntry = typeof window.history.state?.idx === "number" && window.history.state.idx > 0;
    if (canGoBack && hasNextHistoryEntry) {
      router.back();
      return;
    }
    router.push(destination.href);
  }

  // The overview is the home destination; a back button there only points at Documents.
  const currentPath = pathname.split("?")[0].replace(/\/$/, "") || "/dashboard";
  if (currentPath === "/dashboard") return null;

  return (
    <div style={{ display: "flex", alignItems: "center", marginBottom: 20 }}>
      <button
        type="button"
        onClick={goBack}
        aria-label={`Back to ${destination.label}`}
        className="contextual-back-button"
        style={{
          display: "inline-flex", alignItems: "center", gap: 9, padding: "10px 15px",
          border: "1px solid #E5E0D7", borderRadius: 12, background: "linear-gradient(180deg, #FFFFFF 0%, #FAF8F4 100%)",
          color: "#37352F", textDecoration: "none", fontSize: 13, fontWeight: 650,
          boxShadow: "0 3px 10px rgba(31, 28, 20, .05)", cursor: "pointer", transition: "transform 150ms ease, box-shadow 150ms ease",
        }}
      >
        <ArrowLeft size={15} strokeWidth={2.2} />
        <span>Back to {destination.label}</span>
        <CornerUpLeft size={13} style={{ opacity: 0.45, marginLeft: 2 }} />
      </button>
    </div>
  );
}
