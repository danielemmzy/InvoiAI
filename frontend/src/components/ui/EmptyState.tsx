// EmptyState — shown when a list has no items

interface EmptyStateProps {
  icon?: string;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export default function EmptyState({ icon = "📄", title, description, action }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <div className="empty-icon">{icon}</div>
      <div className="empty-title serif">{title}</div>
      {description && <div className="empty-desc">{description}</div>}
      {action}
    </div>
  );
}