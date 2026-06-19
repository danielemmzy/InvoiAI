import { Loader2 } from "lucide-react";

interface SpinnerProps {
  size?: number;
  color?: string;
  fullPage?: boolean;
}

export default function Spinner({
  size = 20,
  color = "#C8922A",
  fullPage = false,
}: SpinnerProps) {
  if (fullPage) {
    return (
      <div className="flex items-center justify-center min-h-screen"
        style={{ background: "#F7F4EE" }}>
        <div className="flex flex-col items-center gap-4">
          <Loader2 size={32} color={color} className="animate-spin" />
          <span className="text-sm" style={{ color: "#6B6860" }}>Loading...</span>
        </div>
      </div>
    );
  }

  return <Loader2 size={size} color={color} className="animate-spin" />;
}