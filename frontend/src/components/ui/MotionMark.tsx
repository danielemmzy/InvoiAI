/**
 * Static, local motion mark (ticket 13).
 *
 * Replaces the remote LottieFiles iframes. The Lottie policy allows local,
 * licensed, lazy-loaded Lottie for meaningful onboarding, success, or empty
 * states only. Until one of those states needs real motion, a static SVG keeps
 * the same composition without a third-party iframe, network request, or
 * animation dependency. Respects reduced motion by not animating at all.
 */
export default function MotionMark({ className }: { className?: string }) {
  return (
    <svg
      className={className ? `motion-mark ${className}` : "motion-mark"}
      viewBox="0 0 120 80"
      aria-hidden="true"
      focusable="false"
    >
      <rect className="mm-paper" x="8" y="6" width="50" height="66" rx="8" />
      <rect className="mm-ink" x="17" y="18" width="24" height="4" rx="2" />
      <rect className="mm-line" x="17" y="28" width="32" height="3" rx="1.5" />
      <rect className="mm-line" x="17" y="36" width="28" height="3" rx="1.5" />
      <rect className="mm-line" x="17" y="44" width="20" height="3" rx="1.5" />
      <path className="mm-path" d="M62 40h14" />
      <path className="mm-path" d="M72 34l7 6-7 6" />
      <circle className="mm-stamp" cx="96" cy="40" r="16" />
      <path className="mm-check" d="M89 40l5 5 9-11" />
    </svg>
  );
}
