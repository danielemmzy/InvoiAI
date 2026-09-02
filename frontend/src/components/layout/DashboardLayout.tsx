"use client";
// DashboardLayout — sidebar + topbar wrapper
//
// RESPONSIVE FIX: .sidebar was position:fixed at a hardcoded 220px
// with zero media query anywhere, and .dash-main had a matching
// hardcoded margin-left:220px. On any phone-width viewport the
// sidebar permanently consumed the whole screen — there was no
// smaller-screen behavior at all, just the desktop layout forced
// onto whatever viewport loaded it. Below 860px the sidebar is now
// a slide-over drawer (off-canvas by default, opened by a hamburger
// button, closed by a backdrop tap or by navigating), matching the
// same pattern already used on the marketing site's mobile nav.

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X, Upload, Zap, LogOut, LayoutDashboard, FileText, ShieldAlert, BookOpen, ShoppingCart, CheckCircle2, Users, Sparkles, Settings, CreditCard, PlugZap, WalletCards, ArrowDownLeft, ArrowUpRight, CalendarClock, Target, Landmark } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useAppStore } from "@/store/useAppStore";
import WorkspaceSwitcher from "./WorkspaceSwitcher";

const BUSINESS_NAV = [
  { section: "Workspace", items: [
    { href: "/dashboard", label: "Overview", icon: LayoutDashboard, exact: true },
    { href: "/dashboard/history", label: "Documents", icon: FileText },
    { href: "/dashboard/upload", label: "Receive document", icon: Upload },
  ]},
  { section: "Accounts payable", items: [
    { href: "/dashboard/ap", label: "AP control center", icon: WalletCards },
    { href: "/dashboard/ap/exceptions", label: "Exceptions", icon: ShieldAlert },
    { href: "/dashboard/approvals", label: "Approvals", icon: CheckCircle2 },
    { href: "/dashboard/purchase-orders", label: "Purchase orders", icon: ShoppingCart },
    { href: "/dashboard/vendors", label: "Vendors", icon: Users },
  ]},
  { section: "Finance", items: [
    { href: "/dashboard/insights", label: "Insights", icon: Sparkles },
    { href: "/integrations", label: "Integrations", icon: PlugZap },
    { href: "/dashboard/billing", label: "Billing", icon: CreditCard },
    { href: "/dashboard/settings", label: "Settings", icon: Settings },
  ]},
];

const PERSONAL_NAV = [
  { section: "Personal", items: [
    { href: "/dashboard/personal", label: "Overview", icon: LayoutDashboard, exact: true },
    { href: "/dashboard/personal/income", label: "Income", icon: ArrowDownLeft },
    { href: "/dashboard/personal/expenses", label: "Expenses", icon: ArrowUpRight },
    { href: "/dashboard/personal/budget", label: "Budget", icon: WalletCards },
    { href: "/dashboard/personal/bills", label: "Bills", icon: CalendarClock },
    { href: "/dashboard/personal/goals", label: "Goals", icon: Target },
    { href: "/dashboard/personal/accounts", label: "Accounts & net worth", icon: Landmark },
    { href: "/dashboard/personal/import", label: "Import statements", icon: FileText },
  ]},
  { section: "Account", items: [
    { href: "/dashboard/settings", label: "Settings", icon: Settings },
    { href: "/dashboard/billing", label: "Billing", icon: CreditCard },
  ]},
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const activeWorkspace = useAppStore((s) => s.activeWorkspace);

  const isActive = (href: string, exact?: boolean) =>
    exact ? pathname === href : pathname.startsWith(href);

  // The icon-only rail only makes sense as a desktop space-saving
  // choice. On the mobile drawer, always show full labels — an
  // icon-only slide-over defeats the point of a drawer that already
  // has the room to spare, and doesn't depend on whatever `collapsed`
  // happened to be set to the last time this was viewed on desktop.
  const showLabels = !collapsed || mobileOpen;

  // Close the mobile drawer automatically whenever the route changes —
  // without this, picking a link leaves the drawer sitting open over
  // the new page underneath it.
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  return (
    <div className="dash-layout">
      {/* Backdrop — mobile only, closes the drawer on tap */}
      {mobileOpen && (
        <div
          className="sidebar-backdrop"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* ── Sidebar ── */}
      <aside className={`sidebar${collapsed ? " collapsed" : ""}${mobileOpen ? " mobile-open" : ""}`}>
        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <Link href="/dashboard" className="sidebar-logo" style={{ flex: 1, borderBottom: "none" }}>
            <div className="sidebar-logo-icon">
              <Zap size={14} color="#C8922A" />
            </div>
            {showLabels && (
              <span className="sidebar-logo-text serif">
                Invoi<span>AI</span>
              </span>
            )}
          </Link>
          <button
            className="sidebar-mobile-close"
            onClick={() => setMobileOpen(false)}
            aria-label="Close navigation"
          >
            <X size={18} />
          </button>
        </div>
        <div style={{ borderBottom: "0.5px solid #E2DDD4" }} />

        {/* Nav */}
        <nav className="sidebar-nav">
          {(activeWorkspace?.type === "personal" ? PERSONAL_NAV : BUSINESS_NAV).map((group) => (
            <div key={group.section}>
              {showLabels && (
                <div className="sidebar-section">{group.section}</div>
              )}
              {group.items.map((item) => {
                const active = isActive(item.href, item.exact);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`sidebar-item${active ? " active" : ""}`}
                    title={collapsed && !mobileOpen ? item.label : undefined}
                    style={{ justifyContent: showLabels ? "flex-start" : "center" }}
                  >
                    <item.icon className="sidebar-icon" size={17} strokeWidth={1.8} />
                    {showLabels && item.label}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>

        {/* User */}
        <div className="sidebar-bottom">
          {showLabels ? (
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
            <button
              className="topbar-hamburger"
              onClick={() => setMobileOpen(true)}
              aria-label="Open navigation"
              aria-expanded={mobileOpen}
            >
              <Menu size={20} />
            </button>
            <WorkspaceSwitcher />
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
            {activeWorkspace?.type !== "personal" && <Link href="/dashboard/upload" className="btn-primary" style={{ padding: "8px 16px", fontSize: 13 }}>
              <Upload size={13} /> Upload
            </Link>}
          </div>
        </div>

        {/* Page content */}
        <div className="dash-body">{children}</div>
      </main>
    </div>
  );
}