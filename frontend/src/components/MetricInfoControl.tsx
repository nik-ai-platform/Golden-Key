import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import { IconButton, Popover, Stack, Typography } from "@mui/material";
import { useId, useState, type MouseEvent } from "react";

import {
  modelProbabilityMarketNote,
  predictionMetricEducation,
  projectedEdgeMarketNote,
  type PredictionMetric,
} from "../data/predictionMetricEducation";

interface MetricInfoControlProps {
  metric: PredictionMetric;
  market?: string;
}

export function MetricInfoControl({ metric, market }: MetricInfoControlProps) {
  const [anchorElement, setAnchorElement] = useState<HTMLElement | null>(null);
  const popoverId = useId();
  const education = predictionMetricEducation[metric];
  const marketNote = metric === "projectedEdge"
    ? projectedEdgeMarketNote(market)
    : metric === "modelProbability"
      ? modelProbabilityMarketNote(market)
      : null;
  const open = Boolean(anchorElement);

  function openPopover(event: MouseEvent<HTMLElement>) {
    setAnchorElement(event.currentTarget);
  }

  function closePopover() {
    setAnchorElement(null);
  }

  return (
    <>
      <IconButton
        aria-label={education.ariaLabel}
        aria-controls={open ? popoverId : undefined}
        aria-expanded={open ? "true" : undefined}
        aria-haspopup="dialog"
        size="small"
        onClick={openPopover}
        sx={{ color: "text.secondary", p: 0.25 }}
      >
        <InfoOutlinedIcon sx={{ fontSize: 15 }} />
      </IconButton>
      <Popover
        id={popoverId}
        open={open}
        anchorEl={anchorElement}
        onClose={closePopover}
        anchorOrigin={{ vertical: "bottom", horizontal: "left" }}
        transformOrigin={{ vertical: "top", horizontal: "left" }}
        slotProps={{
          paper: {
            sx: {
              width: { xs: "calc(100vw - 32px)", sm: 340 },
              maxWidth: "calc(100vw - 32px)",
              boxSizing: "border-box",
              overflowWrap: "anywhere",
              p: 2,
              borderRadius: 1,
            },
          },
        }}
      >
        <Stack spacing={1}>
          <Typography variant="subtitle2" fontWeight={800}>
            {education.title}
          </Typography>
          <Typography variant="body2">{education.short}</Typography>
          {marketNote ? (
            <Typography variant="body2" color="text.secondary">
              {marketNote}
            </Typography>
          ) : null}
          <Typography variant="caption" color="text.secondary">
            {education.disclaimer}
          </Typography>
        </Stack>
      </Popover>
    </>
  );
}
