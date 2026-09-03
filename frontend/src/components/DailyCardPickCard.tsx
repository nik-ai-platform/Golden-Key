import ArrowForwardRoundedIcon from "@mui/icons-material/ArrowForwardRounded";
import StarRoundedIcon from "@mui/icons-material/StarRounded";
import { Box, Button, Card, CardContent, Chip, Stack, Typography } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";

import type { DailyCardPick } from "../types/product";
import { formatAmericanOdds, formatProductDate } from "../utils/productFormat";
import { PickMetrics } from "./PickMetrics";
import { SavePickButton } from "./SavePickButton";

interface DailyCardPickCardProps {
  pick: DailyCardPick;
  prominent?: boolean;
  emphasis?: "default" | "featured" | "premium" | "analytics";
  presentation?: "standard" | "hero" | "compact" | "row";
}

export function DailyCardPickCard({
  pick,
  prominent = false,
  emphasis = "default",
  presentation = "standard",
}: DailyCardPickCardProps) {
  const prediction = pick.prediction;
  const odds = formatAmericanOdds(prediction.american_odds);
  const resolvedEmphasis = prominent ? "premium" : emphasis;
  const isPremium = resolvedEmphasis === "premium";
  const isHero = presentation === "hero";
  const isCompact = presentation === "compact";
  const isRow = presentation === "row";
  const isSideSelection = prediction.selection === "HOME" || prediction.selection === "AWAY";
  const selectionTeam = prediction.selection === "HOME"
    ? prediction.home_team
    : prediction.selection === "AWAY"
      ? prediction.away_team
      : prediction.display_selection;
  const opponent = prediction.selection === "HOME"
    ? prediction.away_team
    : prediction.selection === "AWAY"
      ? prediction.home_team
      : null;
  const selectionDetail = isSideSelection
    ? prediction.display_selection.replace(selectionTeam, "").trim()
    : null;
  const emphasisColor = {
    default: "var(--gk-border)",
    featured: "var(--gk-gold)",
    premium: "var(--gk-gold-bright)",
    analytics: "var(--gk-analytics)",
  }[resolvedEmphasis];
  const emphasisBackground = {
    default: "var(--gk-surface)",
    featured: "var(--gk-gold-soft)",
    premium: "var(--gk-surface-raised)",
    analytics: "var(--gk-analytics-soft)",
  }[resolvedEmphasis];
  const testIdPrefix = isRow ? "daily-game" : "daily-card";

  return (
    <Card
      className={`gk-card${isPremium ? " gk-best-bet" : ""}`}
      variant="outlined"
      data-emphasis={resolvedEmphasis}
      data-testid={`${testIdPrefix}-${pick.role.toLowerCase().replace(/_/g, "-")}`}
      sx={{
        height: "100%",
        borderColor: emphasisColor,
        borderRadius: "var(--gk-radius-sm)",
        backgroundColor: emphasisBackground,
        boxShadow: isPremium ? "0 18px 52px rgba(214, 173, 69, 0.12)" : "none",
        overflow: "hidden",
      }}
    >
      {isHero ? <Box sx={{ height: 3, backgroundColor: "var(--gk-gold-bright)" }} /> : null}
      <CardContent
        sx={{
          p: { xs: 2, sm: 2.5 },
          "&:last-child": { pb: { xs: 2, sm: 2.5 } },
        }}
      >
        <Stack
          direction={isRow ? { xs: "column", md: "row" } : "column"}
          alignItems={isRow ? { xs: "stretch", md: "center" } : "stretch"}
          spacing={isHero ? { xs: 3, sm: 2 } : 2}
        >
          <Stack
            direction="row"
            justifyContent="space-between"
            alignItems="flex-start"
            spacing={1}
            sx={{ flex: isRow ? "1 1 32%" : undefined, minWidth: 0 }}
          >
            <Box>
              <Typography
                variant="overline"
                color={isHero ? "primary.main" : "text.secondary"}
                fontWeight={900}
                sx={{ display: "flex", alignItems: "center", gap: 0.5 }}
              >
                {isHero ? <StarRoundedIcon sx={{ fontSize: 16 }} /> : null}
                {isCompact ? prediction.market : pick.label}
              </Typography>
              {isHero ? (
                <Box sx={{ mt: 1.5 }}>
                  <Typography
                    component="p"
                    sx={{ fontSize: { xs: "1.55rem", sm: "2rem" }, fontWeight: 900, lineHeight: 1.05 }}
                  >
                    {selectionTeam}
                  </Typography>
                  {selectionDetail ? (
                    <Typography
                      component="p"
                      color="primary.main"
                      sx={{ fontSize: { xs: "2rem", sm: "2.75rem" }, fontWeight: 900, lineHeight: 1.15 }}
                    >
                      {selectionDetail}
                    </Typography>
                  ) : null}
                  <Typography color="text.secondary" sx={{ mt: 0.5 }}>
                    {opponent
                      ? `vs ${opponent}`
                      : `${prediction.away_team} @ ${prediction.home_team}`}
                  </Typography>
                </Box>
              ) : (
                <Typography variant={isRow ? "h6" : "h5"} fontWeight={850} sx={{ mt: 0.5 }}>
                  {prediction.display_selection}
                </Typography>
              )}
            </Box>
            {!isCompact ? (
              <Chip
                label={`${prediction.sport} · ${prediction.market}`}
                variant="outlined"
                size="small"
                sx={{ flexShrink: 0, textTransform: "capitalize" }}
              />
            ) : null}
          </Stack>

          {!isHero ? (
            <Box sx={{ flex: isRow ? "1 1 24%" : undefined, minWidth: 0 }}>
              <Typography variant="body2" fontWeight={700}>
                {prediction.away_team} @ {prediction.home_team}
              </Typography>
            <Typography variant="body2" color="text.secondary">
              {formatProductDate(prediction.game_date)}
              {odds ? ` · Odds ${odds}` : ""}
            </Typography>
            </Box>
          ) : null}

          <Box sx={{ flex: isRow ? "1 1 28%" : undefined, minWidth: 0 }}>
            <PickMetrics
              npi={prediction.npi_score}
              confidence={prediction.confidence_score}
              simulationProbability={prediction.simulation_probability}
              projectedEdge={prediction.projected_edge}
              riskLevel={prediction.risk_level}
              focused={presentation !== "standard"}
            />
          </Box>

          {presentation === "standard" || isHero ? (
            <Stack
              direction="row"
              spacing={1}
              flexWrap="wrap"
              useFlexGap
              aria-label="Why this pick ranks here"
            >
              {pick.ranking_reasons.map((reason) => (
                <Chip key={reason} label={reason} size="small" variant="outlined" />
              ))}
            </Stack>
          ) : null}

          <Stack
            direction="row"
            spacing={1}
            flexWrap="wrap"
            useFlexGap
            sx={{ flexShrink: 0, justifyContent: isRow ? { md: "flex-end" } : undefined }}
          >
            <SavePickButton predictionId={prediction.prediction_id} />
            <Button
              component={RouterLink}
              to={`/games/${prediction.game_id}`}
              variant={isHero ? "contained" : "text"}
              endIcon={<ArrowForwardRoundedIcon />}
            >
              View Analysis
            </Button>
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  );
}
