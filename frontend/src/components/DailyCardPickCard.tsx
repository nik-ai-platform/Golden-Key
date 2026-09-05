import ArrowForwardRoundedIcon from "@mui/icons-material/ArrowForwardRounded";
import StarRoundedIcon from "@mui/icons-material/StarRounded";
import { Box, Button, Card, CardContent, Chip, Stack, Typography } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";

import type { DailyCardPick } from "../types/product";
import { formatAmericanOdds, formatProductDate, formatProjectedEdge } from "../utils/productFormat";
import { getPredictionTeamIdentity } from "../utils/teamIdentity";
import { MetricInfoControl } from "./MetricInfoControl";
import { PickMetrics } from "./PickMetrics";
import { SavePickButton } from "./SavePickButton";
import { TeamAccent } from "./TeamAccent";

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
  const teamIdentity = getPredictionTeamIdentity(prediction);
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
  const rankingReasons = pick.ranking_reasons.map((reason) =>
    reason.toLowerCase().includes("projected edge")
      ? `Projected edge ${formatProjectedEdge(prediction.projected_edge, prediction.market)}`
      : reason,
  );

  if (isHero) {
    return (
      <Card
        className="gk-card gk-best-bet"
        variant="outlined"
        data-emphasis={resolvedEmphasis}
        data-testid={`${testIdPrefix}-${pick.role.toLowerCase().replace(/_/g, "-")}`}
        sx={{
          position: "relative",
          borderColor: "var(--gk-gold)",
          borderRadius: "var(--gk-radius-sm)",
          backgroundColor: "var(--gk-surface-raised)",
          boxShadow: "0 14px 42px rgba(214, 173, 69, 0.10)",
          overflow: "hidden",
        }}
      >
        <TeamAccent identity={teamIdentity} variant="glow" testId="best-bet-team-accent" />
        <Box sx={{ height: 3, backgroundColor: "var(--gk-gold-bright)" }} />
        <CardContent sx={{ position: "relative", p: { xs: 2, md: 2.5 }, "&:last-child": { pb: { xs: 2, md: 2.5 } } }}>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "minmax(0, 1fr)", md: "minmax(0, 1.6fr) minmax(300px, 0.75fr)" },
              gap: { xs: 2, md: 3 },
            }}
          >
            <Stack spacing={1.5} justifyContent="space-between" minWidth={0}>
              <Box>
                <Typography
                  variant="overline"
                  color="primary.main"
                  fontWeight={900}
                  sx={{ display: "flex", alignItems: "center", gap: 0.5 }}
                >
                  <StarRoundedIcon sx={{ fontSize: 16 }} />
                  {pick.label}
                </Typography>
                <Typography
                  component="p"
                  sx={{ mt: 0.5, fontSize: { xs: "1.75rem", sm: "2.35rem" }, fontWeight: 900, lineHeight: 1.05 }}
                >
                  {prediction.display_selection}
                </Typography>
                <Typography color="text.secondary" sx={{ mt: 0.75, fontWeight: 650 }}>
                  {prediction.away_team} @ {prediction.home_team}
                </Typography>
              </Box>
              <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap>
                <Chip label={prediction.market} size="small" sx={{ textTransform: "capitalize" }} />
                {odds ? <Chip label={`Odds ${odds}`} size="small" variant="outlined" /> : null}
                <Stack direction="row" alignItems="center" spacing={0.25}>
                  <Chip label={`NPI ${Math.round(prediction.npi_score)}`} size="small" variant="outlined" />
                  <MetricInfoControl metric="npi" market={prediction.market} />
                </Stack>
              </Stack>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap aria-label="Why this pick ranks here">
                {rankingReasons.map((reason) => (
                  <Typography key={reason} variant="caption" color="text.secondary">{reason}</Typography>
                ))}
              </Stack>
            </Stack>

            <Stack spacing={1.5} justifyContent="space-between" sx={{ borderLeft: { md: "1px solid var(--gk-border)" }, pl: { md: 3 } }}>
              <PickMetrics
                npi={prediction.npi_score}
                confidence={prediction.confidence_score}
                simulationProbability={prediction.simulation_probability}
                projectedEdge={prediction.projected_edge}
                riskLevel={prediction.risk_level}
                market={prediction.market}
                hero
              />
              <Stack direction="row" spacing={1} justifyContent={{ md: "flex-end" }} flexWrap="wrap" useFlexGap>
                <SavePickButton predictionId={prediction.prediction_id} />
                <Button component={RouterLink} to={`/games/${prediction.game_id}`} variant="contained" endIcon={<ArrowForwardRoundedIcon />}>
                  View Analysis
                </Button>
              </Stack>
            </Stack>
          </Box>
        </CardContent>
      </Card>
    );
  }

  if (isCompact) {
    const winProbability = prediction.simulation_probability == null
      ? "—"
      : `${prediction.simulation_probability.toFixed(1)}%`;
    const edge = formatProjectedEdge(prediction.projected_edge, prediction.market);

    return (
      <Card
        className="gk-card"
        variant="outlined"
        data-emphasis={resolvedEmphasis}
        data-testid={`${testIdPrefix}-${pick.role.toLowerCase().replace(/_/g, "-")}`}
        sx={{ borderColor: "var(--gk-border)", backgroundColor: "var(--gk-surface)", borderRadius: 0 }}
      >
        <Box
          sx={{
            display: { xs: "block", md: "grid" },
            gridTemplateColumns: { md: "minmax(190px, 1.5fr) minmax(220px, 1.4fr) 90px 110px 90px" },
            alignItems: "center",
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.25, px: { xs: 2, md: 1.5 }, pt: { xs: 2, md: 1.25 }, pb: { xs: 0, md: 1.25 }, minWidth: 0 }}>
            <TeamAccent identity={teamIdentity} variant="dot" testId="market-leader-team-accent" />
            <Box minWidth={0}>
              <Typography variant="overline" color="primary.main" fontWeight={900}>{pick.label}</Typography>
              <Typography fontWeight={850} noWrap>{prediction.display_selection}</Typography>
            </Box>
          </Box>
          <Box sx={{ px: { xs: 2, md: 1.5 }, py: { xs: 1, md: 1.25 }, minWidth: 0 }}>
            <Typography variant="body2" fontWeight={700} noWrap>{prediction.away_team} @ {prediction.home_team}</Typography>
            <Typography variant="caption" color="text.secondary">{formatProductDate(prediction.game_date)}</Typography>
          </Box>
          {[
            { label: "Odds", value: odds ?? "—", color: "text.primary" },
            { label: "Win prob", value: winProbability, color: "text.primary" },
            { label: "Edge", value: edge, color: "var(--gk-analytics)" },
          ].map((metric) => (
            <Box key={metric.label} sx={{ display: { xs: "none", md: "block" }, px: 1.5, py: 1.25, borderLeft: "1px solid var(--gk-border)" }}>
              <Typography fontFamily="monospace" fontWeight={800} color={metric.color}>
                {metric.label === "Odds" ? (
                  <Box
                    component="span"
                    sx={{ display: "none" }}
                  >
                    Odds{" "}
                  </Box>
                ) : null}
                {metric.value}
              </Typography>
            </Box>
          ))}
          <Box sx={{ display: { md: "none" }, px: 2, pb: 1 }}>
            <PickMetrics
              npi={prediction.npi_score}
              confidence={prediction.confidence_score}
              simulationProbability={prediction.simulation_probability}
              projectedEdge={prediction.projected_edge}
              riskLevel={prediction.risk_level}
              market={prediction.market}
              focused
            />
          </Box>
          <Stack direction="row" spacing={1} sx={{ display: { md: "none" }, px: 2, pb: 2 }}>
            <SavePickButton predictionId={prediction.prediction_id} />
            <Button component={RouterLink} to={`/games/${prediction.game_id}`} variant="text" endIcon={<ArrowForwardRoundedIcon />}>
              View Analysis
            </Button>
          </Stack>
        </Box>
      </Card>
    );
  }

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
      <CardContent
        sx={{
          p: { xs: 2, sm: 2.5 },
          "&:last-child": { pb: { xs: 2, sm: 2.5 } },
        }}
      >
        <Stack
          direction={isRow ? { xs: "column", md: "row" } : "column"}
          alignItems={isRow ? { xs: "stretch", md: "center" } : "stretch"}
          spacing={2}
        >
          <Stack
            direction="row"
            justifyContent="space-between"
            alignItems="flex-start"
            spacing={1}
            sx={{ flex: isRow ? "1 1 32%" : undefined, minWidth: 0 }}
          >
            <Box>
              {isRow ? (
                <Stack direction="row" alignItems="center" spacing={1}>
                  <TeamAccent identity={teamIdentity} variant="bar" testId="game-row-team-accent" />
                  <Box minWidth={0}>
                    <Typography
                      variant="overline"
                      color="text.secondary"
                      fontWeight={900}
                    >
                      {pick.label}
                    </Typography>
                    <Typography variant="h6" fontWeight={850} sx={{ mt: 0.5 }}>
                      {prediction.display_selection}
                    </Typography>
                  </Box>
                </Stack>
              ) : (
                <>
              <Typography
                variant="overline"
                color="text.secondary"
                fontWeight={900}
                sx={{ display: "flex", alignItems: "center", gap: 0.5 }}
              >
                {pick.label}
              </Typography>
              <Typography variant={isRow ? "h6" : "h5"} fontWeight={850} sx={{ mt: 0.5 }}>
                {prediction.display_selection}
              </Typography>
                </>
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

          <Box sx={{ flex: isRow ? "1 1 24%" : undefined, minWidth: 0 }}>
              <Typography variant="body2" fontWeight={700}>
                {prediction.away_team} @ {prediction.home_team}
              </Typography>
            <Typography variant="body2" color="text.secondary">
              {formatProductDate(prediction.game_date)}
              {odds ? ` · Odds ${odds}` : ""}
            </Typography>
          </Box>

          <Box sx={{ flex: isRow ? "1 1 28%" : undefined, minWidth: 0 }}>
            <PickMetrics
              npi={prediction.npi_score}
              confidence={prediction.confidence_score}
              simulationProbability={prediction.simulation_probability}
              projectedEdge={prediction.projected_edge}
              riskLevel={prediction.risk_level}
              market={prediction.market}
              focused={presentation !== "standard"}
            />
          </Box>

          {presentation === "standard" ? (
            <Stack
              direction="row"
              spacing={1}
              flexWrap="wrap"
              useFlexGap
              aria-label="Why this pick ranks here"
            >
              {rankingReasons.map((reason) => (
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
