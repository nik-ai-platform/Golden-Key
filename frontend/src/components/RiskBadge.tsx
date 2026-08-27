import { Chip } from "@mui/material";

export function RiskBadge({ risk }: { risk: string | null }) {
  const normalized = risk?.toLowerCase() ?? "unrated";
  const color = normalized === "low" ? "success" : normalized === "medium" ? "warning" : normalized === "high" ? "error" : "default";

  return <Chip label={`${normalized} risk`} size="small" color={color} variant="outlined" sx={{ textTransform: "uppercase", letterSpacing: 0.5 }} />;
}
