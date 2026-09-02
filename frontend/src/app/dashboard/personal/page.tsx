"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ArrowDownLeft,
  ArrowUpRight,
  WalletCards,
  Target,
  Plus,
  Landmark,
  AlertTriangle,
} from "lucide-react";
import DashboardLayout from "@/components/layout/DashboardLayout";
import { useFinance } from "@/hooks/useFinance";

const money = (n: number | undefined | null) =>
  new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n || 0);

type FinanceData = {
  net_worth?: number;
  assets?: number;
  liabilities?: number;
  income?: number;
  spending?: number;
  cash_flow?: number;
  active_goals?: any[];
  spending_by_category?: Record<string, number>;
  accounts?: any[];
};

export default function Page() {
  const { summary, alerts } = useFinance();
  const [show, setShow] = useState(false);

  const d: FinanceData = summary.data ?? {};

  if (summary.isLoading) {
    return (
      <DashboardLayout>
        <div className="dash-page-header">
          <div className="section-label">Personal / Overview</div>
          <div className="dash-title serif">
            Your financial picture
          </div>
        </div>

        <div className="card" style={{ padding: 32 }}>
          Loading your financial picture…
        </div>
      </DashboardLayout>
    );
  }

  if (summary.isError) {
    return (
      <DashboardLayout>
        <div className="card" style={{ padding: 32 }}>
          <b>We couldn't load your finances.</b>

          <p style={{ margin: "8px 0 16px" }}>
            Your data is safe. Try again.
          </p>

          <button
            className="btn-primary"
            onClick={() => summary.refetch()}
          >
            Retry
          </button>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="dash-page-header">
        <div className="section-label">Personal / Overview</div>

        <div className="dash-title serif">
          Your financial picture.
        </div>

        <div className="dash-subtitle">
          See what you have, what you spend, what is coming next,
          and where you're heading.
        </div>
      </div>

      <div
        style={{
          display: "flex",
          gap: 10,
          flexWrap: "wrap",
          marginBottom: 22,
        }}
      >
        <Link
          className="btn-primary"
          href="/dashboard/personal/expenses"
        >
          <Plus size={16} />
          Add transaction
        </Link>

        <Link
          className="btn-ghost"
          href="/dashboard/personal/budget"
        >
          Plan this month
        </Link>

        <Link
          className="btn-ghost"
          href="/dashboard/personal/goals"
        >
          Fund a goal
        </Link>
      </div>

      {/* Metrics */}
      <div className="metrics-grid">
        <Metric
          icon={<WalletCards />}
          label="Net worth"
          value={money(d.net_worth)}
          sub={`${money(d.assets)} assets · ${money(
            d.liabilities
          )} liabilities`}
        />

        <Metric
          icon={<ArrowDownLeft />}
          label="Income this month"
          value={money(d.income)}
          sub="Money in"
        />

        <Metric
          icon={<ArrowUpRight />}
          label="Spending this month"
          value={money(d.spending)}
          sub={`${money(d.cash_flow)} net cash flow`}
        />

        <Metric
          icon={<Target />}
          label="Active goals"
          value={String(d.active_goals?.length || 0)}
          sub="Keep moving forward"
        />
      </div>

      <div className="dash-grid">
        {/* Spending by category */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">
              Spending by category
            </span>

            <Link
              className="card-action"
              href="/dashboard/personal/expenses"
            >
              View activity
            </Link>
          </div>

          <div style={{ padding: 22 }}>
            {Object.keys(d.spending_by_category || {}).length ? (
              Object.entries(d.spending_by_category || {})
                .sort((a, b) => b[1] - a[1])
                .slice(0, 6)
                .map(([k, v]) => {
                  const spending = d.spending || 0;

                  const percentage =
                    spending > 0
                      ? Math.min(100, (v / spending) * 100)
                      : 0;

                  return (
                    <div
                      key={k}
                      style={{ marginBottom: 14 }}
                    >
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          fontSize: 13,
                          marginBottom: 5,
                        }}
                      >
                        <span>
                          {k.replace("_", " ")}
                        </span>

                        <b>{money(v)}</b>
                      </div>

                      <div
                        style={{
                          height: 7,
                          background: "#eee9df",
                          borderRadius: 9,
                        }}
                      >
                        <div
                          style={{
                            height: "100%",
                            width: `${percentage}%`,
                            background: "#C8922A",
                            borderRadius: 9,
                          }}
                        />
                      </div>
                    </div>
                  );
                })
            ) : (
              <div className="empty-state">
                <div className="empty-title serif">
                  Your spending story starts here
                </div>

                <div className="empty-desc">
                  Add a few transactions and InvoiAI will
                  organize your spending automatically.
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Accounts */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Accounts</span>

            <Link
              className="card-action"
              href="/dashboard/personal/accounts"
            >
              Manage
            </Link>
          </div>

          <div style={{ padding: 18 }}>
            {d.accounts?.length ? (
              d.accounts.slice(0, 5).map((a: any) => (
                <div
                  key={a.id}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    padding: "11px 4px",
                    borderBottom: "1px solid #eee9df",
                  }}
                >
                  <span>
                    <Landmark
                      size={14}
                      style={{
                        verticalAlign: "-2px",
                        marginRight: 8,
                      }}
                    />

                    {a.name}
                  </span>

                  <b>{money(a.current_balance)}</b>
                </div>
              ))
            ) : (
              <div className="empty-state">
                <div className="empty-title serif">
                  Connect your financial life
                </div>

                <div className="empty-desc">
                  Add checking, savings, cash, credit or
                  investment accounts. Bank-sync connectors can
                  plug into the same model later.
                </div>

                <Link
                  className="btn-amber"
                  href="/dashboard/personal/accounts"
                >
                  Add account
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Alerts */}
      {alerts.data?.length ? (
        <div
          className="card"
          style={{ marginTop: 18 }}
        >
          <div className="card-header">
            <span
              className="card-title"
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
              }}
            >
              <AlertTriangle size={15} />
              Things to notice
            </span>
          </div>

          <div style={{ padding: 18 }}>
            {alerts.data.slice(0, 4).map((a: any) => (
              <div
                key={a.id}
                style={{ padding: "10px 0" }}
              >
                <b>{a.title}</b>

                <div className="dash-subtitle">
                  {a.message}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </DashboardLayout>
  );
}

function Metric({
  icon,
  label,
  value,
  sub,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub: string;
}) {
  return (
    <div className="metric-card">
      <div
        className="metric-label"
        style={{
          display: "flex",
          gap: 7,
          alignItems: "center",
        }}
      >
        {icon}
        {label}
      </div>

      <div className="metric-value serif">
        {value}
      </div>

      <div className="metric-change">
        {sub}
      </div>
    </div>
  );
}