"use client";
// DashboardLayout — sidebar + topbar wrapper

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X, Upload, Zap, LogOut, LayoutDashboard, FileText, CreditCard, Settings } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useAppStore } from "@/store/useAppStore";

const NAV = [
  {
    section: "Monitor",
    items: [
      { href: "/dashboard", label: "Overview", icon: "◻", exact: true },
      { href: "/dashboard/history", label: "Documents", icon: "≡" },
    ],
  },
  {
    section: "Process",
    items: [
      { href: "/dashboard/upload", label: "Upload", icon: "↑" },
    ],
  },
  {
    section: "Account",
    items: [
      { href: "/dashboard/billing", label: "Billing", icon: "◇" },
      { href: "/dashboard/settings", label: "Settings", icon: "⊙" },
    ],
  },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();
  const { user, logout } = useAuth();

  const isActive = (href: string, exact?: boolean) =>
    exact ? pathname === href : pathname.startsWith(href);

  return (
    <div className="dash-layout">
      {/* ── Sidebar ── */}
      <aside className={`sidebar${collapsed ? " collapsed" : ""}`}>
        {/* Logo */}
        <Link href="/dashboard" className="sidebar-logo">
          <div className="sidebar-logo-icon">
            <Zap size={14} color="#C8922A" />
          </div>
          {!collapsed && (
            <span className="sidebar-logo-text serif">
              Invoi<span>AI</span>
            </span>
          )}
        </Link>

        {/* Nav */}
        <nav className="sidebar-nav">
          {NAV.map((group) => (
            <div key={group.section}>
              {!collapsed && (
                <div className="sidebar-section">{group.section}</div>
              )}
              {group.items.map((item) => {
                const active = isActive(item.href, item.exact);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`sidebar-item${active ? " active" : ""}`}
                    title={collapsed ? item.label : undefined}
                    style={{ justifyContent: collapsed ? "center" : "flex-start" }}
                  >
                    <span className="sidebar-icon">{item.icon}</span>
                    {!collapsed && item.label}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>

        {/* User */}
        <div className="sidebar-bottom">
          {!collapsed ? (
            <div className="user-pill">
              <div className="avatar">
                {user?.email?.[0]?.toUpperCase() || "U"}
              </div>
              <div className="user-info">
                <div className="user-name">{user?.email}</div>
                <div className="user-plan">
                  <div className="plan-dot" />
                  {user?.plan || "free"}
                </div>
              </div>
              <button className="logout-btn" onClick={() => logout()} title="Sign out">
                <LogOut size={14} />
              </button>
            </div>
          ) : (
            <button
              className="logout-btn"
              onClick={() => logout()}
              style={{ width: "100%", display: "flex", justifyContent: "center", padding: "8px" }}
              title="Sign out"
            >
              <LogOut size={16} />
            </button>
          )}
        </div>
      </aside>

      {/* ── Main ── */}
      <main className={`dash-main${collapsed ? " expanded" : ""}`}>
        {/* Topbar */}
        <div className="dash-topbar">
          <div className="topbar-left">
            <button className="topbar-toggle" onClick={() => setCollapsed(!collapsed)}>
              {collapsed ? <Menu size={18} /> : <X size={18} />}
            </button>
          </div>
          <div className="topbar-right">
            {user?.usage && (
              <div className="usage-pill">
                {user.usage.used}/{user.usage.limit} docs this month
              </div>
            )}
            <Link href="/dashboard/upload" className="btn-primary" style={{ padding: "8px 16px", fontSize: 13 }}>
              <Upload size={13} /> Upload
            </Link>
          </div>
        </div>

        {/* Page content */}
        <div className="dash-body">{children}</div>
      </main>
    </div>
  );
}