"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import { X } from "lucide-react";

export interface MobileMenuLink {
  href: string;
  label: string;
}

interface MobileMenuProps {
  open: boolean;
  onClose: () => void;
  links: MobileMenuLink[];
  ctaHref: string;
  ctaLabel: string;
  secondaryHref?: string;
  secondaryLabel?: string;
}

/**
 * Full-screen mobile navigation takeover — a distinct interaction from the
 * inline horizontal desktop nav, not a shrunken copy of it. Locks body
 * scroll, closes on Escape or backdrop click, and returns focus to the
 * trigger on close.
 */
export default function MobileMenu({
  open,
  onClose,
  links,
  ctaHref,
  ctaLabel,
  secondaryHref,
  secondaryLabel,
}: MobileMenuProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const firstLinkRef = useRef<HTMLAnchorElement>(null);

  useEffect(() => {
    if (!open) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    firstLinkRef.current?.focus();

    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (e.key === "Tab" && panelRef.current) {
        const focusable = panelRef.current.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled])'
        );
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <>
      <div className="mobile-menu-backdrop" onClick={onClose} aria-hidden="true" />
      <div
        className="mobile-menu-panel"
        role="dialog"
        aria-modal="true"
        aria-label="Site navigation"
        ref={panelRef}
      >
        <div className="mobile-menu-header">
          <span className="nav-logo serif">
            Invoi<span>AI</span>
          </span>
          <button
            type="button"
            className="mobile-menu-close"
            aria-label="Close menu"
            onClick={onClose}
          >
            <X size={22} />
          </button>
        </div>

        <div className="mobile-menu-body">
          <nav className="mobile-menu-links" aria-label="Primary">
            {links.map((link, i) => (
              <Link
                key={link.href}
                href={link.href}
                className="mobile-menu-link"
                onClick={onClose}
                ref={i === 0 ? firstLinkRef : undefined}
                style={{ animationDelay: `${0.08 + i * 0.05}s` }}
              >
                <span className="mobile-menu-link-num">{String(i + 1).padStart(2, "0")}</span>
                <span className="mobile-menu-link-label">{link.label}</span>
              </Link>
            ))}
          </nav>
        </div>

        <div className="mobile-menu-footer">
          <Link href={ctaHref} className="mobile-menu-cta" onClick={onClose}>
            {ctaLabel}
          </Link>
          {secondaryHref && secondaryLabel && (
            <Link href={secondaryHref} className="mobile-menu-secondary" onClick={onClose}>
              {secondaryLabel}
            </Link>
          )}
        </div>
      </div>
    </>
  );
}
