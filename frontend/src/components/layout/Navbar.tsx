"use client";
// Navbar.tsx — top navigation bar for landing page

import Link from "next/link";
import { useAppStore } from "@/store/useAppStore";
import { Zap } from "lucide-react";

export default function Navbar() {
  const { isAuthenticated } = useAppStore();

  return (
    <nav
      className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-12 h-16"
      style={{
        background: "rgba(247,244,238,0.92)",
        backdropFilter: "blur(12px)",
        borderBottom: "0.5px solid #E2DDD4",
      }}
    >
      {/* Logo */}
      <Link href="/" className="flex items-center gap-2.5">
        <div
          className="w-7 h-7 rounded-md flex items-center justify-center"
          style={{ background: "#1A1916" }}
        >
          <Zap size={14} color="#C8922A" />
        </div>
        <span
          style={{
            fontFamily: "'Playfair Display', serif",
            fontSize: 20,
            fontWeight: 700,
            color: "#1A1916",
            letterSpacing: "-0.5px",
          }}
        >
          Invoi<span style={{ color: "#C8922A" }}>AI</span>
        </span>
      </Link>

      {/* Nav links */}
      <div className="flex items-center gap-8">
        {["Pricing", "Industries", "Docs"].map((l) => (
          <span
            key={l}
            className="text-sm cursor-pointer transition-colors"
            style={{ color: "#6B6860", fontFamily: "'DM Sans', sans-serif" }}
          >
            {l}
          </span>
        ))}

        {isAuthenticated ? (
          <Link
            href="/dashboard"
            className="text-sm font-medium px-5 py-2.5 rounded-lg transition-all"
            style={{
              background: "#1A1916",
              color: "#FFFFFF",
              fontFamily: "'DM Sans', sans-serif",
            }}
          >
            Go to dashboard →
          </Link>
        ) : (
          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="text-sm font-medium px-4 py-2 rounded-lg transition-all"
              style={{ color: "#1A1916", fontFamily: "'DM Sans', sans-serif" }}
            >
              Sign in
            </Link>
            <Link
              href="/signup"
              className="text-sm font-medium px-5 py-2.5 rounded-lg transition-all"
              style={{
                background: "#1A1916",
                color: "#FFFFFF",
                fontFamily: "'DM Sans', sans-serif",
              }}
            >
              Get started →
            </Link>
          </div>
        )}
      </div>
    </nav>
  );
}