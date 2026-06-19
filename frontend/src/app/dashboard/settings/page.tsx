"use client";
// Settings page — /dashboard/settings

import { useQuery } from "@tanstack/react-query";
import { ExternalLink, Loader2 } from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { useAuth } from "@/hooks/useAuth";
import { useAppStore } from "@/store/useAppStore";
import { authApi } from "@/api/auth";

export default function SettingsPage() {
  const { user } = useAppStore();
  const { logout, connectGoogle, isConnectingGoogle } = useAuth();

  const { data: googleStatus } = useQuery({
    queryKey: ["googleStatus"],
    queryFn: authApi.getGoogleStatus,
  });

  return (
    <DashboardLayout>
      <div className="dash-page-header">
        <div className="section-label">§04 Account / Settings</div>
        <div className="dash-title serif">Settings</div>
        <div className="dash-subtitle">Manage your account and integrations.</div>
      </div>

      <div style={{ maxWidth: 520, display: "flex", flexDirection: "column", gap: 16 }}>

        {/* Account info */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Account</span>
          </div>
          <div style={{ padding: "4px 0" }}>
            {[
              { label: "Email", value: user?.email },
              { label: "User ID", value: user?.user_id?.slice(0, 16) + "..." },
              { label: "Plan", value: user?.plan?.toUpperCase() || "FREE", isTag: true },
            ].map((row) => (
              <div key={row.label} className="settings-row" style={{ padding: "14px 20px" }}>
                <div>
                  <div className="settings-key">{row.label}</div>
                </div>
                {row.isTag ? (
                  <span className="badge badge-industry">{row.value}</span>
                ) : (
                  <span className="settings-val">{row.value}</span>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Google Sheets */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Google Sheets Integration</span>
          </div>
          <div style={{ padding: "16px 20px" }}>
            <p style={{ fontSize: 13, color: "#6B6860", lineHeight: 1.6, marginBottom: 16 }}>
              Connect your Google account to export documents directly to your
              Google Drive as Sheets. No billing required.
            </p>

            {googleStatus?.google_connected ? (
              <div className="connected-badge">
                <div className="connected-dot" />
                <span className="connected-text">Google account connected</span>
              </div>
            ) : (
              <button
                onClick={() => connectGoogle()}
                disabled={isConnectingGoogle}
                className="btn-primary"
                style={{ fontSize: 13, padding: "10px 18px" }}
              >
                {isConnectingGoogle
                  ? <><Loader2 size={14} className="animate-spin" /> Connecting...</>
                  : <><ExternalLink size={14} /> Connect Google Account</>
                }
              </button>
            )}
          </div>
        </div>

        {/* Danger zone */}
        <div className="card" style={{ border: "0.5px solid #FDECEA" }}>
          <div className="card-header" style={{ borderColor: "#FDECEA" }}>
            <span className="card-title" style={{ color: "#E57373" }}>Danger Zone</span>
          </div>
          <div style={{ padding: "16px 20px" }}>
            <div className="settings-row" style={{ borderBottom: "none", padding: 0 }}>
              <div>
                <div className="settings-key">Sign out</div>
                <div className="settings-sub">Sign out of your InvoiAI account on this device.</div>
              </div>
              <button className="btn-danger" onClick={() => logout()}>
                Sign out
              </button>
            </div>
          </div>
        </div>

      </div>
    </DashboardLayout>
  );
}