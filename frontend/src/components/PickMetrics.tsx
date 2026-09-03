import { Box, Chip, Divider, Typography } from "@mui/material";

import { formatConfidence, formatNpi } from "../utils/productFormat";

interface PickMetricsProps {
  npi: number;
  confidence: number | null;
  simulationProbability: number | null;
  projectedEdge: number | null;
  riskLevel: string | null;
  focused?: boolean;
}

function formatPercentage(value: number | null): string {
  return value == null || !Number.isFinite(value) ? "—" : formatConfidence(value);
}

function formatEdge(value: number | null): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return `${value > 0 ? "+" : ""}${value.toFixed(1)}%`;
}

function riskLabel(value: string | null): string | null {
  if (!value) return null;
  const normalized = value.toLowerCase();
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

function riskColor(
  value: string | null,
): "success" | "warning" | "error" | "default" {
  const normalized = value?.toUpperCase();
  if (normalized === "LOW") return "success";
  if (normalized === "MEDIUM") return "warning";
  if (normalized === "HIGH") return "error";
  return "default";
}

const labelSx = {
  color: "text.secondary",
  fontSize: "0.72rem",
  fontWeight: 600,
  letterSpacing: "0.04em",
  lineHeight: 1.25,
  overflowWrap: "anywhere",
  textTransform: "uppercase",
};

export function PickMetrics({
  npi,
  confidence,
  simulationProbability,
  projectedEdge,
  riskLevel,
  focused = false,
}: PickMetricsProps) {
  const risk = riskLabel(riskLevel);
  const keyMetrics = [
    { label: "NPI", value: Number.isFinite(npi) ? Math.round(npi).toString() : "—" },
    { label: "Confidence", value: formatPercentage(confidence) },
    { label: "Edge", value: formatEdge(projectedEdge) },
  ];
  const metrics = [
    { label: "Confidence", value: formatPercentage(confidence) },
    { label: "Simulation", value: formatPercentage(simulationProbability) },
    { label: "Edge", value: formatEdge(projectedEdge) },
  ];

  if (focused) {
    return (
      <Box
        data-testid="pick-metrics"
        sx={{
          display: "grid",
          gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
          borderBlock: "1px solid",
          borderColor: "var(--gk-border)",
          py: 1.5,
        }}
      >
        {keyMetrics.map((metric, index) => (
          <Box
            key={metric.label}
            sx={{
              minWidth: 0,
              px: { xs: index === 0 ? 0 : 1, sm: index === 0 ? 0 : 1.25 },
              borderLeft: index === 0 ? 0 : "1px solid var(--gk-border)",
            }}
          >
            <Typography sx={{ ...labelSx, overflowWrap: "normal", whiteSpace: "nowrap" }}>
              {metric.label}
            </Typography>
            <Typography
              sx={{
                color: metric.label === "Edge" ? "var(--gk-analytics)" : "text.primary",
                fontSize: { xs: "1rem", sm: "1.15rem" },
                fontWeight: 800,
                lineHeight: 1.4,
                overflowWrap: "anywhere",
              }}
            >
              {metric.value}
            </Typography>
          </Box>
        ))}
      </Box>
    );
  }

  return (
    <Box
      data-testid="pick-metrics"
      sx={{
        backgroundColor: "action.hover",
        border: "1px solid",
        borderColor: "divider",
        borderRadius: 2,
        p: { xs: 1.5, sm: 2 },
        minWidth: 0,
      }}
    >
      <Box>
        <Typography sx={labelSx}>NPI</Typography>
        <Typography sx={{ fontSize: "1.25rem", fontWeight: 700, lineHeight: 1.35 }}>
          {formatNpi(npi)}
        </Typography>
      </Box>

      <Divider sx={{ my: 1.25 }} />

      <Box
        data-testid="supporting-metrics"
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "repeat(2, minmax(0, 1fr))", md: "repeat(4, minmax(0, 1fr))" },
          columnGap: { xs: 2, md: 0.75 },
          rowGap: 1.5,
        }}
      >
        {metrics.map((metric) => (
          <Box key={metric.label} sx={{ minWidth: 0 }}>
            <Typography sx={labelSx}>{metric.label}</Typography>
            <Typography sx={{ fontSize: "1rem", fontWeight: 700, lineHeight: 1.4, overflowWrap: "anywhere" }}>
              {metric.value}
            </Typography>
          </Box>
        ))}
        <Box sx={{ minWidth: 0 }}>
          <Typography sx={labelSx}>Risk</Typography>
          {risk ? (
            <Chip
              label={risk}
              color={riskColor(riskLevel)}
              size="small"
              variant="outlined"
              sx={{ mt: 0.25, height: 24, fontWeight: 700 }}
            />
          ) : (
            <Typography sx={{ fontSize: "1rem", fontWeight: 700, lineHeight: 1.4 }}>
              —
            </Typography>
          )}
        </Box>
      </Box>
    </Box>
  );
}