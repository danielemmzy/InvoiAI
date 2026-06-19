// Badge — reusable status badge

interface BadgeProps {
  children: React.ReactNode;
  variant?: "done" | "industry" | "warning" | "error" | "muted";
}

const classMap = {
  done: "badge badge-done",
  industry: "badge badge-industry",
  warning: "badge badge-warning",
  error: "badge badge-error",
  muted: "badge badge-muted",
};

export default function Badge({ children, variant = "muted" }: BadgeProps) {
  return <span className={classMap[variant]}>{children}</span>;
}