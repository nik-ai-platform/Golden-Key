import ArrowDownwardRoundedIcon from "@mui/icons-material/ArrowDownwardRounded";
import { Box, Link, Stack, Typography } from "@mui/material";
import type { ReactNode } from "react";

import {
  dashboardSequence,
  npiBandsExplanation,
  npiBandsNotice,
  npiMarketEducation,
  predictionMetricEducation,
  projectedEdgeEducation,
  responsibleInterpretation,
  riskThresholds,
} from "../data/predictionMetricEducation";

const pageLinks = [
  { label: "The numbers", href: "#the-numbers" },
  { label: "How picks are chosen", href: "#how-picks-are-chosen" },
  { label: "A note on risk", href: "#responsible-use" },
];

function EducationPanel({
  id,
  title,
  intro,
  children,
}: {
  id: string;
  title: string;
  intro?: string;
  children: ReactNode;
}) {
  return (
    <Box
      component="section"
      aria-labelledby={`${id}-title`}
      id={id}
      sx={{
        minWidth: 0,
        p: { xs: 2, sm: 3 },
        border: "1px solid var(--gk-border-strong)",
        borderRadius: 1,
        backgroundColor: "background.paper",
        scrollMarginTop: 3,
      }}
    >
      <Typography
        id={`${id}-title`}
        component="h2"
        variant="h5"
        className="gk-editorial"
        sx={{ mb: intro ? 0.75 : 1.5 }}
      >
        {title}
      </Typography>
      {intro ? (
        <Typography color="text.secondary" sx={{ maxWidth: 760, lineHeight: 1.75, mb: 2 }}>
          {intro}
        </Typography>
      ) : null}
      {children}
    </Box>
  );
}

function ExplanationCards({
  items,
}: {
  items: readonly { title: string; description: string }[];
}) {
  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: {
          xs: "minmax(0, 1fr)",
          md: "repeat(3, minmax(0, 1fr))",
        },
        gap: 1.5,
        mt: 2,
      }}
    >
      {items.map((item) => (
        <Box
          key={item.title}
          sx={{
            minWidth: 0,
            p: 2,
            border: "1px solid var(--gk-border)",
            borderTop: "2px solid var(--gk-gold)",
            backgroundColor: "var(--gk-surface-soft)",
          }}
        >
          <Typography
            component="h3"
            variant="subtitle2"
            fontFamily="var(--gk-font-mono)"
            sx={{ mb: 1 }}
          >
            {item.title}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.75 }}>
            {item.description}
          </Typography>
        </Box>
      ))}
    </Box>
  );
}

function MetricGuide({
  title,
  description,
  note,
}: {
  title: string;
  description: string;
  note: string;
}) {
  return (
    <Box
      sx={{
        minWidth: 0,
        p: { xs: 1.75, sm: 2.25 },
        border: "1px solid var(--gk-border)",
        backgroundColor: "var(--gk-surface-soft)",
      }}
    >
      <Typography component="h3" variant="subtitle1" fontWeight={800} sx={{ mb: 0.75 }}>
        {title}
      </Typography>
      <Typography variant="body2" sx={{ lineHeight: 1.75 }}>
        {description}
      </Typography>
      <Typography
        variant="caption"
        color="text.secondary"
        sx={{ display: "block", mt: 1, lineHeight: 1.6 }}
      >
        {note}
      </Typography>
    </Box>
  );
}

export function HowItWorksPage() {
  return (
    <Stack spacing={{ xs: 1.5, sm: 2.5 }} sx={{ maxWidth: 1120, mx: "auto", minWidth: 0 }}>
      <Box
        component="header"
        sx={{
          py: { xs: 1.5, sm: 3 },
          px: { xs: 0, sm: 1 },
          borderBottom: "1px solid var(--gk-border-strong)",
        }}
      >
        <Typography variant="overline" color="primary.main">
          Bear A Hand Sports / A simple guide
        </Typography>
        <Typography
          component="h1"
          className="gk-editorial"
          sx={{
            maxWidth: 780,
            fontSize: { xs: "2.25rem", sm: "3.25rem", md: "4rem" },
            lineHeight: 1.05,
            my: 1,
          }}
        >
          How to Read Your Picks
        </Typography>
        <Typography color="text.secondary" sx={{ maxWidth: 760, lineHeight: 1.8 }}>
          A pick brings together a game, a market, and a few model signals. Here is what
          those signals mean, how a pick makes it to the dashboard, and what they cannot
          tell you.
        </Typography>
        <Box
          component="nav"
          aria-label="On this page"
          sx={{
            display: "flex",
            flexWrap: "wrap",
            gap: 1,
            mt: 2.5,
          }}
        >
          {pageLinks.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              underline="none"
              sx={{
                px: 1.25,
                py: 0.75,
                border: "1px solid var(--gk-border-strong)",
                color: "text.primary",
                fontSize: "0.875rem",
                fontWeight: 700,
                "&:hover": { borderColor: "primary.main", color: "primary.main" },
                "&:focus-visible": { outline: "2px solid", outlineColor: "primary.main", outlineOffset: 2 },
              }}
            >
              {item.label}
            </Link>
          ))}
        </Box>
      </Box>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "repeat(3, minmax(0, 1fr))" },
          gap: 1.25,
        }}
      >
        {[
          {
            title: "Start with the recommended pick",
            text: "Read the selection first: the team, OVER, or UNDER recommended for that market. Then check the matchup, market, and current sportsbook price before reading the model numbers.",
          },
          {
            title: "The numbers",
            text: "Each number answers a different question. Confidence is not the chance to win.",
          },
          {
            title: "The outcome",
            text: "These are estimates, not promises. Games are uncertain, and prices can change.",
          },
        ].map((item, index) => (
          <Box
            key={item.title}
            sx={{
              p: 2,
              borderTop: "2px solid var(--gk-gold)",
              backgroundColor: "var(--gk-surface-soft)",
            }}
          >
            <Typography
              variant="overline"
              color="text.secondary"
              sx={{ fontFamily: "var(--gk-font-mono)" }}
            >
              0{index + 1} / {item.title}
            </Typography>
            <Typography variant="body2" sx={{ mt: 0.5, lineHeight: 1.7 }}>
              {item.text}
            </Typography>
          </Box>
        ))}
      </Box>

      <EducationPanel
        id="best-pick"
        title="What does Best Pick mean?"
        intro="Best Pick is a recommendation within the dashboard's eligible picks, not a promise that it will win."
      >
        <Typography variant="body2" sx={{ lineHeight: 1.75 }}>
          Read the reasons shown with the pick to understand why it ranks there. The
          recommendation, Confidence Rating, Model Probability, and Risk Level answer
          different questions. Best Pick does not mean the lowest risk, the highest
          chance to win, or guaranteed profit.
        </Typography>
        <Typography component="h3" variant="subtitle1" fontWeight={800} sx={{ mt: 2, mb: 0.75 }}>
          Why can a Best Pick have Medium risk?
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.75 }}>
          Best Pick describes the recommendation; Medium risk describes its Confidence
          Rating, from 65 through 79.99. A pick can be recommended and still carry that
          risk label. Medium is not a personal bankroll assessment, and Best Pick does
          not remove uncertainty.
        </Typography>
      </EducationPanel>

      <EducationPanel
        id="the-numbers"
        title="What the numbers mean"
        intro="Think of these as different pieces of context, not one combined promise. Read each number for its own market and question."
      >
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
            gap: 1.25,
          }}
        >
          <MetricGuide
            title="NPI Score"
            description="NPI is a model score, not a chance to win. Its meaning depends on the market: spread, moneyline, and total scores describe different things."
            note="Compare NPI only within the same market and model context. A higher spread NPI does not always mean more support for the selected side."
          />
          <MetricGuide
            title={predictionMetricEducation.modelProbability.title}
            description="This is the model's estimated likelihood of the displayed selection: a team, OVER, or UNDER."
            note="The methods differ by market, and these estimates are not yet presented as fully calibrated probabilities. They are not guarantees."
          />
          <MetricGuide
            title={predictionMetricEducation.confidence.title}
            description="Confidence Rating is a 0–95 score that combines NPI, the size of the projected edge, and the model-probability input."
            note="Confidence is not win probability or a percent chance to win. It describes model conviction."
          />
          <MetricGuide
            title={predictionMetricEducation.projectedEdge.title}
            description="Projected Edge compares the model with a market-specific reference point."
            note="Spread and moneyline edges are percentage-point differences; total edge is a scoring-point difference. It is not a universal expected-profit figure."
          />
          <MetricGuide
            title={predictionMetricEducation.risk.title}
            description="Risk Level currently comes from Confidence Rating. It is not a separate measure of volatility or personal bankroll risk."
            note="Low: 80 or higher. Medium: 65 through 79.99. High: below 65. These labels do not say how much to wager."
          />
        </Box>
      </EducationPanel>

      <EducationPanel
        id="npi-markets"
        title="Why NPI depends on the market"
        intro={predictionMetricEducation.npi.detailed}
      >
        <ExplanationCards items={npiMarketEducation} />
      </EducationPanel>

      <EducationPanel
        id="npi-score-ranges"
        title="NPI Band"
        intro={npiBandsExplanation}
      >
        <Box
          sx={{
            display: "flex",
            alignItems: "flex-start",
            gap: 1,
            p: 1.5,
            borderLeft: "2px solid var(--gk-gold)",
            backgroundColor: "var(--gk-surface-soft)",
          }}
        >
          <ArrowDownwardRoundedIcon color="primary" sx={{ mt: 0.25, fontSize: 18 }} />
          <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.7 }}>
            {npiBandsNotice}
          </Typography>
        </Box>
      </EducationPanel>

      <EducationPanel
        id="edge-by-market"
        title="What “projected edge” compares"
        intro={predictionMetricEducation.projectedEdge.detailed}
      >
        <ExplanationCards items={projectedEdgeEducation} />
      </EducationPanel>

      <EducationPanel
        id="risk-levels"
        title="How Risk Level is labeled"
        intro={predictionMetricEducation.risk.detailed}
      >
        <ExplanationCards items={riskThresholds} />
      </EducationPanel>

      <EducationPanel
        id="how-picks-are-chosen"
        title="How picks are chosen"
        intro="Every published pick follows the same broad path:"
      >
        <Box
          component="ol"
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", sm: "repeat(2, minmax(0, 1fr))" },
            gap: 1,
            m: 0,
            p: 0,
            listStyle: "none",
            counterReset: "steps",
          }}
        >
          {dashboardSequence.map((step, index) => (
            <Box
              component="li"
              key={step}
              sx={{
                display: "flex",
                alignItems: "flex-start",
                gap: 1.25,
                minWidth: 0,
                p: 1.5,
                border: "1px solid var(--gk-border)",
                backgroundColor: "var(--gk-surface-soft)",
              }}
            >
              <Typography
                component="span"
                aria-hidden="true"
                sx={{
                  flex: "0 0 auto",
                  color: "primary.main",
                  fontFamily: "var(--gk-font-mono)",
                  fontWeight: 700,
                }}
              >
                {String(index + 1).padStart(2, "0")}
              </Typography>
              <Typography component="span" variant="body2" sx={{ lineHeight: 1.7 }}>
                {step}
              </Typography>
            </Box>
          ))}
        </Box>
      </EducationPanel>

      <EducationPanel
        id="responsible-use"
        title="A note on uncertainty"
        intro="Sports are unpredictable. Use the information to understand a model's view—not as a promise of what will happen."
      >
        <Box
          component="ul"
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", sm: "repeat(2, minmax(0, 1fr))" },
            gap: 1,
            m: 0,
            p: 0,
            listStyle: "none",
          }}
        >
          {responsibleInterpretation.map((item) => (
            <Box
              component="li"
              key={item}
              sx={{
                minWidth: 0,
                p: 1.5,
                borderLeft: "2px solid var(--gk-analytics)",
                backgroundColor: "var(--gk-surface-soft)",
              }}
            >
              <Typography variant="body2" sx={{ lineHeight: 1.7 }}>
                {item}
              </Typography>
            </Box>
          ))}
        </Box>
      </EducationPanel>
    </Stack>
  );
}
