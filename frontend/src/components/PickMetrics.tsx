import { Box, Chip, Divider, LinearProgress, Stack, Typography } from "@mui/material";

import type { PredictionMetric } from "../data/predictionMetricEducation";
import { formatConfidence, formatNpi } from "../utils/productFormat";
import { MetricInfoControl } from "./MetricInfoControl";

interface PickMetricsProps {
  npi: number;
  confidence: number | null;
  simulationProbability: number | null;
  projectedEdge: number | null;
  riskLevel: string | null;
  market?: string;
  focused?: boolean;
  hero?: boolean;
}

function formatPercentage(value: number | null): string {
  return value == null || !Number.isFinite(value) ? "—" : formatConfidence(value);
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
  fontSize: "0.65rem",
  fontWeight: 600,
  letterSpacing: "0.02em",
  lineHeight: 1.15,
  overflowWrap: "normal",
  wordBreak: "normal",
  textTransform: "uppercase",
};

function MetricLabel({
  label,
  metric,
  market,
}: {
  label: string;
  metric: PredictionMetric;
  market?: string;
}) {
  const canWrapAtWordBoundary = label === "Model Probability";

  return (
    <Stack
      direction="row"
      alignItems={canWrapAtWordBoundary ? "flex-end" : "center"}
      spacing={0.25}
    >
      <Typography
        data-testid={`metric-label-${metric}`}
        sx={{
          ...labelSx,
          minWidth: 0,
          whiteSpace: canWrapAtWordBoundary ? "normal" : "nowrap",
        }}
      >
        {label}
      </Typography>
      <MetricInfoControl metric={metric} market={market} />
    </Stack>
  );
}

export function PickMetrics({
  npi,
  confidence,
  simulationProbability,
  riskLevel,
  market,
  focused = false,
  hero = false,
}: PickMetricsProps) {
  const risk = riskLabel(riskLevel);
  const keyMetrics = [
    { label: "NPI", value: Number.isFinite(npi) ? Math.round(npi).toString() : "—", metric: "npi" as const },
    { label: "Confidence", value: formatPercentage(confidence), metric: "confidence" as const },
  ];
  const metrics = [
    { label: "Confidence", value: formatPercentage(confidence), metric: "confidence" as const },
    { label: "Model Probability", value: formatPercentage(simulationProbability), metric: "modelProbability" as const },
  ];

  if (hero) {
    const confidenceValue = confidence == null || !Number.isFinite(confidence)
      ? 0
      : Math.max(0, Math.min(confidence, 100));

    return (
      <Box data-testid="pick-metrics">
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: "minmax(0, 1fr)",
            border: "1px solid var(--gk-border-strong)",
            backgroundColor: "rgba(0, 0, 0, 0.18)",
          }}
        >
          {[
            { label: "Model Probability", value: formatPercentage(simulationProbability), metric: "modelProbability" as const },
          ].map((metric) => (
            <Box
              key={metric.label}
              sx={{
                minWidth: 0,
                px: { xs: 1.5, sm: 2 },
                py: { xs: 1, sm: 1.25 },
              }}
            >
              <MetricLabel label={metric.label} metric={metric.metric} market={market} />
              <Typography
                sx={{
                  mt: 0.25,
                  color: "text.primary",
                  fontSize: { xs: "1.3rem", sm: "1.65rem" },
                  fontWeight: 900,
                  lineHeight: 1.15,
                }}
              >
                {metric.value}
              </Typography>
            </Box>
          ))}
        </Box>
        <Stack direction="row" alignItems="center" spacing={1.5} sx={{ mt: 1.25 }}>
          <Box sx={{ minWidth: 88 }}>
            <MetricLabel label="Confidence" metric="confidence" market={market} />
            <Typography fontWeight={850}>{formatPercentage(confidence)}</Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={confidenceValue}
            aria-label="Confidence"
            sx={{
              flexGrow: 1,
              height: 5,
              borderRadius: 0,
              backgroundColor: "var(--gk-border)",
              "& .MuiLinearProgress-bar": { backgroundColor: "var(--gk-gold)" },
            }}
          />
        </Stack>
      </Box>
    );
  }

  if (focused) {
    return (
      <Box
        data-testid="pick-metrics"
        sx={{
          display: "grid",
          gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
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
            <MetricLabel label={metric.label} metric={metric.metric} market={market} />
            <Typography
              sx={{
                color: "text.primary",
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
        <MetricLabel label="NPI" metric="npi" market={market} />
        <Typography sx={{ fontSize: "1.25rem", fontWeight: 700, lineHeight: 1.35 }}>
          {formatNpi(npi)}
        </Typography>
      </Box>

      <Divider sx={{ my: 1.25 }} />

      <Box
        data-testid="supporting-metrics"
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "repeat(2, minmax(0, 1fr))", md: "repeat(3, minmax(0, 1fr))" },
          columnGap: { xs: 2, md: 0.75 },
          rowGap: 1.5,
        }}
      >
        {metrics.map((metric) => (
          <Box key={metric.label} sx={{ minWidth: 0 }}>
            <MetricLabel label={metric.label} metric={metric.metric} market={market} />
            <Typography sx={{ fontSize: "1rem", fontWeight: 700, lineHeight: 1.4, overflowWrap: "anywhere" }}>
              {metric.value}
            </Typography>
          </Box>
        ))}
        <Box sx={{ minWidth: 0 }}>
          <Typography
            data-testid="metric-label-risk"
            sx={{ ...labelSx, whiteSpace: "nowrap" }}
          >
            Risk
          </Typography>
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