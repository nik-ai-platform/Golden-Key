import { Box, Stack, Typography } from "@mui/material";
import type { ReactNode } from "react";

import {
  dashboardSequence, npiBandsExplanation, npiBandsNotice, npiMarketEducation,
  predictionMetricEducation, projectedEdgeEducation, responsibleInterpretation, riskThresholds,
} from "../data/predictionMetricEducation";

function EducationPanel({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <Box component="section" aria-labelledby={id} sx={{
      minWidth: 0, p: { xs: 2, sm: 3 }, border: "1px solid var(--gk-border-strong)",
      borderRadius: 1, backgroundColor: "background.paper",
    }}>
      <Typography id={id} component="h2" variant="h5" className="gk-editorial" sx={{ mb: 1.5 }}>
        {title}
      </Typography>
      {children}
    </Box>
  );
}

function ExplanationCards({ items }: { items: readonly { title: string; description: string }[] }) {
  return (
    <Box sx={{ display: "grid", gridTemplateColumns: { xs: "minmax(0, 1fr)", md: "repeat(3, minmax(0, 1fr))" }, gap: 1.5, mt: 2 }}>
      {items.map((item) => (
        <Box key={item.title} sx={{ minWidth: 0, p: 2, border: "1px solid var(--gk-border)", borderTop: "2px solid var(--gk-gold)", backgroundColor: "var(--gk-surface-soft)" }}>
          <Typography component="h3" variant="subtitle2" fontFamily="var(--gk-font-mono)" sx={{ mb: 1 }}>{item.title}</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.75 }}>{item.description}</Typography>
        </Box>
      ))}
    </Box>
  );
}

export function HowItWorksPage() {
  return (
    <Stack spacing={2.5} sx={{ maxWidth: 1120, mx: "auto", minWidth: 0 }}>
      <Box component="header" sx={{ py: { xs: 1, sm: 2 } }}>
        <Typography variant="overline" color="primary.main">Bear A Hand Sports / Metric Education</Typography>
        <Typography component="h1" className="gk-editorial" sx={{ fontSize: { xs: "2rem", sm: "2.75rem", md: "3.25rem" }, lineHeight: 1.1, my: 1 }}>
          How the Intelligence Works
        </Typography>
        <Typography color="text.secondary" sx={{ maxWidth: 800, lineHeight: 1.8 }}>
          Bear A Hand Sports separates model scoring, estimated probability, model-to-market edge, and confidence so users can understand what each number represents. These metrics are analytical estimates—not guarantees.
        </Typography>
      </Box>
      <EducationPanel id="education-npi" title="Nik Power Index (NPI)">
        <Typography sx={{ lineHeight: 1.8 }}>{predictionMetricEducation.npi.detailed}</Typography>
        <ExplanationCards items={npiMarketEducation} />
      </EducationPanel>
      <EducationPanel id="education-bands" title="NPI bands">
        <Typography sx={{ lineHeight: 1.8 }}>{npiBandsExplanation}</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 2, pl: 2, borderLeft: "2px solid var(--gk-gold)" }}>{npiBandsNotice}</Typography>
      </EducationPanel>
      <EducationPanel id="education-probability" title="Model Probability">
        <Typography sx={{ lineHeight: 1.8 }}>{predictionMetricEducation.modelProbability.detailed}</Typography>
      </EducationPanel>
      <EducationPanel id="education-confidence" title="Confidence Rating">
        <Typography sx={{ lineHeight: 1.8 }}>{predictionMetricEducation.confidence.detailed}</Typography>
      </EducationPanel>
      <EducationPanel id="education-edge" title="Projected Edge">
        <Typography sx={{ lineHeight: 1.8 }}>{predictionMetricEducation.projectedEdge.detailed}</Typography>
        <ExplanationCards items={projectedEdgeEducation} />
      </EducationPanel>
      <EducationPanel id="education-risk" title="Risk Level">
        <Typography sx={{ lineHeight: 1.8 }}>{predictionMetricEducation.risk.detailed}</Typography>
        <ExplanationCards items={riskThresholds} />
      </EducationPanel>
      <EducationPanel id="education-sequence" title="How a pick reaches the dashboard">
        <Box component="ol" sx={{ m: 0, pl: 3, "& li": { pl: 1, py: 0.75, "&::marker": { color: "primary.main", fontFamily: "var(--gk-font-mono)" } } }}>
          {dashboardSequence.map((step) => <Typography component="li" key={step}>{step}</Typography>)}
        </Box>
      </EducationPanel>
      <EducationPanel id="education-responsible" title="Responsible interpretation">
        <Box component="ul" sx={{ m: 0, pl: 3, "& li": { py: 0.5, "&::marker": { color: "info.main" } } }}>
          {responsibleInterpretation.map((item) => <Typography component="li" key={item}>{item}</Typography>)}
        </Box>
      </EducationPanel>
    </Stack>
  );
}
