"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  Building2,
  Check,
  ChevronDown,
  Loader2,
  Sparkles,
  UserRound,
} from "lucide-react";
import {
  useCreateWorkspace,
  useWorkspaces,
} from "@/hooks/useWorkspaces";

import type {
  CompanySize,
  WorkspaceType,
} from "@/types/workspace";

const COUNTRIES = [
  { value: "NG", label: "Nigeria", currency: "NGN" },
  { value: "GH", label: "Ghana", currency: "GHS" },
  { value: "KE", label: "Kenya", currency: "KES" },
  { value: "ZA", label: "South Africa", currency: "ZAR" },
  { value: "GB", label: "United Kingdom", currency: "GBP" },
  { value: "US", label: "United States", currency: "USD" },
  { value: "CA", label: "Canada", currency: "CAD" },
  { value: "AU", label: "Australia", currency: "AUD" },
  { value: "AE", label: "United Arab Emirates", currency: "AED" },
  { value: "SA", label: "Saudi Arabia", currency: "SAR" },
  { value: "DE", label: "Germany", currency: "EUR" },
  { value: "FR", label: "France", currency: "EUR" },
  { value: "NL", label: "Netherlands", currency: "EUR" },
];

const CURRENCIES = [
  ["NGN", "Nigerian Naira", "₦"],
  ["USD", "US Dollar", "$"],
  ["GBP", "British Pound", "£"],
  ["EUR", "Euro", "€"],
  ["CAD", "Canadian Dollar", "C$"],
  ["AUD", "Australian Dollar", "A$"],
  ["GHS", "Ghanaian Cedi", "GH₵"],
  ["KES", "Kenyan Shilling", "KSh"],
  ["ZAR", "South African Rand", "R"],
  ["AED", "UAE Dirham", "د.إ"],
  ["SAR", "Saudi Riyal", "﷼"],
] as const;

const COMPANY_SIZES: {
  value: CompanySize;
  label: string;
  description: string;
}[] = [
  {
    value: "1",
    label: "Just me",
    description: "Solo operator",
  },
  {
    value: "2-10",
    label: "2–10",
    description: "Small team",
  },
  {
    value: "11-50",
    label: "11–50",
    description: "Growing team",
  },
  {
    value: "51-200",
    label: "51–200",
    description: "Established",
  },
  {
    value: "201-500",
    label: "201–500",
    description: "Large company",
  },
  {
    value: "500+",
    label: "500+",
    description: "Enterprise",
  },
];

export default function WorkspacePage() {
  const {
    data: workspaces,
    isLoading,
    isError,
  } = useWorkspaces();

  const createWorkspace = useCreateWorkspace();

  const [type, setType] = useState<WorkspaceType | null>(null);
  const [businessName, setBusinessName] = useState("");
  const [companySize, setCompanySize] =
    useState<CompanySize | null>(null);

  const [country, setCountry] = useState("NG");
  const [currency, setCurrency] = useState("NGN");

  const personalExists = useMemo(
    () =>
      workspaces?.some(
        (workspace) => workspace.type === "personal"
      ) ?? false,
    [workspaces]
  );

  /*
   * ============================================================
   * READ OPTIONAL URL INTENT
   * ============================================================
   */

  useEffect(() => {
    const requested =
      typeof window !== "undefined"
        ? new URLSearchParams(window.location.search).get("create")
        : null;

    if (
      requested === "personal" &&
      personalExists
    ) {
      window.location.replace("/dashboard");
      return;
    }

    if (
      requested === "personal" ||
      requested === "business"
    ) {
      setType(requested);
    }
  }, [personalExists]);

  /*
   * ============================================================
   * EXISTING USERS
   * ============================================================
   */

  useEffect(() => {
    const requested =
      typeof window !== "undefined"
        ? new URLSearchParams(window.location.search).get("create")
        : null;

    /*
     * If the user already has a workspace and they did not
     * explicitly ask to create another one, dashboard is the
     * correct destination.
     */
    if (
      !isLoading &&
      workspaces &&
      workspaces.length > 0 &&
      !requested
    ) {
      window.location.replace("/dashboard");
    }

  }, [isLoading, workspaces]);

  /*
   * ============================================================
   * CREATE
   * ============================================================
   */

  function handleCountryChange(nextCountry: string) {
    setCountry(nextCountry);

    const selected = COUNTRIES.find(
      (item) => item.value === nextCountry
    );

    if (selected) {
      setCurrency(selected.currency);
    }
  }

  function handleCreateWorkspace() {
    if (!type || createWorkspace.isPending) {
      return;
    }

    if (
      type === "business" &&
      (
        businessName.trim().length < 2 ||
        !companySize
      )
    ) {
      return;
    }

    createWorkspace.mutate({
      type,

      /*
       * Personal workspaces deliberately do not need a name.
       *
       * The backend creates:
       *
       *     "Personal"
       *
       * automatically.
       */
      name:
        type === "business"
          ? businessName.trim()
          : undefined,

      company_size:
        type === "business"
          ? companySize!
          : undefined,

      country,
      currency,
    });
  }

  /*
   * ============================================================
   * LOADING
   * ============================================================
   */

  if (isLoading) {
    return (
      <div className="workspace-page">
        <div className="workspace-loading-card">
          <Loader2
            size={22}
            className="animate-spin"
          />

          <span>
            Preparing your workspace...
          </span>
        </div>
      </div>
    );
  }

  /*
   * ============================================================
   * ERROR
   * ============================================================
   */

  if (isError) {
    return (
      <div className="workspace-page">
        <div className="workspace-error-card">
          <div className="workspace-error-icon">
            !
          </div>

          <h1>
            We couldn&apos;t load your workspace.
          </h1>

          <p>
            Your account is safe. Refresh the page and we&apos;ll
            try again.
          </p>

          <button
            type="button"
            className="workspace-primary-button"
            onClick={() => window.location.reload()}
          >
            Try again
            <ArrowRight size={16} />
          </button>
        </div>
      </div>
    );
  }

  /*
   * ============================================================
   * ONBOARDING
   * ============================================================
   */

  return (
    <div className="workspace-page">
      {/* Background decoration */}

      <div className="workspace-orb workspace-orb-one" />
      <div className="workspace-orb workspace-orb-two" />

      {/* Brand */}

      <div className="workspace-topbar">
        <div className="workspace-brand-new">
          <span className="workspace-brand-mark">
            <Sparkles size={15} />
          </span>

          <span>
            Invoi<span>AI</span>
          </span>
        </div>

        <div className="workspace-progress">
          <span className="workspace-progress-active">
            03
          </span>

          <span />
          <span />
        </div>
      </div>

      <main className="workspace-content">
        <div className="workspace-heading">
          <p className="workspace-eyebrow">
            Step 03 · Create your workspace
          </p>

          <h1>
            Where will you
            <br />
            <span>manage your money?</span>
          </h1>

          <p>
            Choose the space you want to create first. You can add
            another workspace later and switch between them from
            your dashboard.
          </p>
        </div>

        {/* ======================================================
            TYPE SELECTION
            ====================================================== */}

        <div className="workspace-choice-grid">
          {/* PERSONAL */}

          <button
            type="button"
            disabled={personalExists}
            onClick={() => {
              if (!personalExists) {
                setType("personal");
              }
            }}
            className={`workspace-choice ${
              type === "personal"
                ? "workspace-choice-selected personal"
                : ""
            } ${
              personalExists
                ? "workspace-choice-disabled"
                : ""
            }`}
          >
            <div className="workspace-choice-top">
              <div className="workspace-choice-icon personal">
                <UserRound size={22} />
              </div>

              {personalExists ? (
                <span className="workspace-existing">
                  Already created
                </span>
              ) : type === "personal" ? (
                <span className="workspace-selected-check">
                  <Check size={14} />
                </span>
              ) : (
                <ArrowRight size={17} />
              )}
            </div>

            <div className="workspace-choice-copy">
              <h2>Personal</h2>

              <p>
                Manage your personal income, expenses, bills,
                budgets, debts, savings and financial goals.
              </p>
            </div>

            <div className="workspace-choice-tags">
              <span>Income</span>
              <span>Expenses</span>
              <span>Goals</span>
            </div>
          </button>

          {/* BUSINESS */}

          <button
            type="button"
            onClick={() => setType("business")}
            className={`workspace-choice ${
              type === "business"
                ? "workspace-choice-selected business"
                : ""
            }`}
          >
            <div className="workspace-choice-top">
              <div className="workspace-choice-icon business">
                <Building2 size={22} />
              </div>

              {type === "business" ? (
                <span className="workspace-selected-check">
                  <Check size={14} />
                </span>
              ) : (
                <ArrowRight size={17} />
              )}
            </div>

            <div className="workspace-choice-copy">
              <h2>Business</h2>

              <p>
                Manage invoices, accounts payable, vendors,
                approvals, finance operations and accounting
                integrations.
              </p>
            </div>

            <div className="workspace-choice-tags">
              <span>Invoices</span>
              <span>AP</span>
              <span>Finance</span>
            </div>
          </button>
        </div>

        {/* ======================================================
            BUSINESS DETAILS
            ====================================================== */}

        {type === "business" && (
          <section className="business-details">
            <div className="business-details-header">
              <div>
                <p className="workspace-eyebrow">
                  Business details
                </p>

                <h2>
                  Tell us about your company.
                </h2>

                <p>
                  This helps us personalize your workspace.
                </p>
              </div>

              <Building2 size={22} />
            </div>

            <div className="business-field">
              <label htmlFor="business-name">
                Business name
              </label>

              <input
                id="business-name"
                type="text"
                value={businessName}
                onChange={(event) =>
                  setBusinessName(event.target.value)
                }
                placeholder="e.g. Acme Construction Ltd"
                maxLength={120}
                autoFocus
              />

              <span>
                Use the name your team recognizes.
              </span>
            </div>

            <div className="business-field">
              <label>
                How many people work there?
              </label>

              <div className="company-size-grid-new">
                {COMPANY_SIZES.map((size) => {
                  const selected =
                    companySize === size.value;

                  return (
                    <button
                      type="button"
                      key={size.value}
                      onClick={() =>
                        setCompanySize(size.value)
                      }
                      className={`company-size-option ${
                        selected
                          ? "selected"
                          : ""
                      }`}
                    >
                      <span className="company-size-check">
                        {selected && (
                          <Check size={12} />
                        )}
                      </span>

                      <span>
                        <strong>
                          {size.label}
                        </strong>

                        <small>
                          {size.description}
                        </small>
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="business-field">
              <label htmlFor="workspace-country">
                Country
              </label>

              <div className="workspace-select-wrap">
                <select
                  id="workspace-country"
                  value={country}
                  onChange={(event) =>
                    handleCountryChange(event.target.value)
                  }
                >
                  {COUNTRIES.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
                <ChevronDown size={16} />
              </div>

              <span>
                Used to personalize your financial workspace.
              </span>
            </div>

            <div className="business-field">
              <label htmlFor="workspace-currency">
                Reporting currency
              </label>

              <div className="workspace-select-wrap">
                <select
                  id="workspace-currency"
                  value={currency}
                  onChange={(event) =>
                    setCurrency(event.target.value)
                  }
                >
                  {CURRENCIES.map(([code, label, symbol]) => (
                    <option key={code} value={code}>
                      {code} · {label} ({symbol})
                    </option>
                  ))}
                </select>
                <ChevronDown size={16} />
              </div>

              <span>
                This becomes your default reporting currency. Invoices
                can still keep their original transaction currency.
              </span>
            </div>
          </section>
        )}

        {type === "personal" && (
          <section className="business-details">
            <div className="business-details-header">
              <div>
                <p className="workspace-eyebrow">
                  Financial setup
                </p>
                <h2>Choose your reporting currency.</h2>
                <p>
                  Your personal transactions can still use other
                  currencies when your plan supports multi-currency.
                </p>
              </div>
              <UserRound size={22} />
            </div>

            <div className="business-field">
              <label htmlFor="personal-country">
                Country
              </label>

              <div className="workspace-select-wrap">
                <select
                  id="personal-country"
                  value={country}
                  onChange={(event) =>
                    handleCountryChange(event.target.value)
                  }
                >
                  {COUNTRIES.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
                <ChevronDown size={16} />
              </div>
            </div>

            <div className="business-field">
              <label htmlFor="personal-currency">
                Reporting currency
              </label>

              <div className="workspace-select-wrap">
                <select
                  id="personal-currency"
                  value={currency}
                  onChange={(event) =>
                    setCurrency(event.target.value)
                  }
                >
                  {CURRENCIES.map(([code, label, symbol]) => (
                    <option key={code} value={code}>
                      {code} · {label} ({symbol})
                    </option>
                  ))}
                </select>
                <ChevronDown size={16} />
              </div>

              <span>
                This is the default currency used for your financial
                reporting.
              </span>
            </div>
          </section>
        )}

        {/* ======================================================
            CREATE BUTTON
            ====================================================== */}

        <div className="workspace-action">
          <button
            type="button"
            onClick={handleCreateWorkspace}
            disabled={
              !type ||
              createWorkspace.isPending ||
              (
                type === "business" &&
                (
                  businessName.trim().length < 2 ||
                  !companySize
                )
              )
            }
            className="workspace-primary-button"
          >
            {createWorkspace.isPending ? (
              <>
                <Loader2
                  size={17}
                  className="animate-spin"
                />

                Creating workspace...
              </>
            ) : (
              <>
                Create{" "}
                {type === "personal"
                  ? "personal"
                  : "business"}{" "}
                workspace

                <ArrowRight size={17} />
              </>
            )}
          </button>

          <p>
            Your workspace will be ready immediately after creation.
          </p>
        </div>
      </main>
    </div>
  );
}
