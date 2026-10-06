import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import { IconButton, Link, Popover, Stack, Typography } from "@mui/material";
import { useId, useState, type MouseEvent } from "react";
import { Link as RouterLink } from "react-router-dom";

import {
  modelProbabilityMarketNote,
  npiMarketNote,
  predictionMetricEducation,
  projectedEdgeEducation,
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
  const marketNote = metric === "modelProbability"
    ? modelProbabilityMarketNote(market)
    : metric === "npi" && market ? npiMarketNote(market)
      : metric === "projectedEdge" ? projectedEdgeEducation.find((item) => item.market === market?.toLowerCase())?.description
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
            role: "dialog",
            "aria-label": education.title,
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
          <Link component={RouterLink} to="/how-it-works" onClick={closePopover} sx={{ fontSize: "0.875rem", py: 0.5 }}>
            Learn how all metrics work
          </Link>
        </Stack>
      </Popover>
    </>
  );
}
