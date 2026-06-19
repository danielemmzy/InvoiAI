"use client";
// Sidebar.tsx — dashboard sidebar navigation
// Extracted from DashboardLayout so it can be used independently

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, FileText, Upload,
  History, CreditCard, Settings,
  LogOut, Zap,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useAppStore } from "@/store/useAppStore";
import { cn } from "@/lib/utils";

const NAV_GROUPS = [
  {
    section: "Monitor",
    items: [
      { href: "/dashboard", label: "Overview", icon: LayoutDashboard, exact: true },
      { href: "/dashboard/history", label: "Documents", icon: FileText },
    ],
  },
  {
    section: "Process",
    items: [
      { href: "/dashboard/upload", label: "Upload", icon: Upload },
    ],
  },
  {
    section: "Account",
    items: [
      { href: "/dashboard/billing", label: "Billing", icon: CreditCard },
      { href: "/dashboard/settings", label: "Settings", icon: Settings },
    ],
  },
];

const planColors: Record<string, string> = {
  free: "#888",
  starter: "#C8922A",
  pro: "#1E7E4B",
};

interface SidebarProps {
  collapsed?: boolean;
}

export default function Sidebar({ collapsed = false }: SidebarProps) {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  const isActive = (href: string, exact?: boolean) =>
    exact ? pathname === href : pathname.startsWith(href);

  return (
    <aside
      className={cn(
        "flex flex-col h-full transition-all duration-300",
        collapsed ? "w-[60px]" : "w-[220px]"
      )}
      style={{ background: "#FFFFFF", borderRight: "0.5px solid #E2DDD4" }}
    >
      {/* Logo */}
      <div
        className="flex items-center gap-3 px-5 py-5 flex-shrink-0"
        style={{ borderBottom: "0.5px solid #E2DDD4" }}
      >
        <div
          className="w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0"
          style={{ background: "#1A1916" }}
        >
          <Zap size={14} color="#C8922A" />
        </div>
        {!collapsed && (
          <span
            style={{
              fontFamily: "'Playfair Display', serif",
              fontSize: 18,
              fontWeight: 700,
              color: "#1A1916",
            }}
          >
            Invoi<span style={{ color: "#C8922A" }}>AI</span>
          </span>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4 px-3">
        {NAV_GROUPS.map((group) => (
          <div key={group.section} className="mb-5">
            {!collapsed && (
              <div
                className="px-3 mb-2 text-xs font-medium uppercase tracking-widest"
                style={{ color: "#AAA8A0" }}
              >
                {group.section}
              </div>
            )}
            {group.items.map((item) => {
              const active = isActive(item.href, item.exact);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  title={collapsed ? item.label : undefined}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2.5 rounded-lg mb-0.5 transition-all text-sm",
                    collapsed && "justify-center"
                  )}
                  style={{
                    background: active ? "#F7F4EE" : "transparent",
                    color: active ? "#1A1916" : "#6B6860",
                    fontWeight: active ? 500 : 400,
                    borderLeft: active && !collapsed
                      ? "3px solid #C8922A"
                      : "3px solid transparent",
                    fontFamily: "'DM Sans', sans-serif",
                  }}
                >
                  <item.icon size={16} className="flex-shrink-0" />
                  {!collapsed && item.label}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* User section */}
      <div
        className="p-3 flex-shrink-0"
        style={{ borderTop: "0.5px solid #E2DDD4" }}
      >
        {!collapsed ? (
          <div
            className="flex items-center gap-2 px-2 py-2 rounded-lg mb-2"
            style={{ background: "#F7F4EE" }}
          >
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold flex-shrink-0"
              style={{ background: "#F5E6C8", color: "#C8922A" }}
            >
              {user?.email?.[0]?.toUpperCase() || "U"}
            </div>
            <div className="flex-1 min-w-0">
              <div
                className="text-xs font-medium truncate"
                style={{ color: "#1A1916" }}
              >
                {user?.email}
              </div>
              <div className="flex items-center gap-1.5 mt-0.5">
                <div
                  className="w-1.5 h-1.5 rounded-full"
                  style={{ background: planColors[user?.plan || "free"] }}
                />
                <span className="text-xs capitalize" style={{ color: "#6B6860" }}>
                  {user?.plan || "free"}
                </span>
              </div>
            </div>
            <button
              onClick={() => logout()}
              className="p-1 rounded transition-colors flex-shrink-0"
              style={{ color: "#AAA8A0" }}
              title="Logout"
            >
              <LogOut size={14} />
            </button>
          </div>
        ) : (
          <button
            onClick={() => logout()}
            className="w-full flex justify-center p-2 rounded-lg"
            style={{ color: "#6B6860" }}
            title="Logout"
          >
            <LogOut size={16} />
          </button>
        )}
      </div>
    </aside>
  );
}