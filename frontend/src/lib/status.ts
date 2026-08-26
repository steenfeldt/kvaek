const COLORS: Record<string, string> = {
  draft: "neutral",
  active: "success",
  completed: "info",
  cancelled: "neutral",
  sent: "neutral",
  declined: "error",
  negotiating: "warning",
  accepted: "success",
  closed: "neutral",
  open: "warning",
  superseded: "neutral",
};

export function statusColor(status: string): any {
  return COLORS[status] ?? "neutral";
}
