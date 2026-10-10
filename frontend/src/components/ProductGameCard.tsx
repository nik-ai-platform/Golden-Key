import ArrowForwardOutlinedIcon from "@mui/icons-material/ArrowForwardOutlined";
import InsightsOutlinedIcon from "@mui/icons-material/InsightsOutlined";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Stack,
  Typography,
} from "@mui/material";
import { Link as RouterLink } from "react-router-dom";

import type { Prediction } from "../types/product";
import { getPredictionTeam, getTeamIdentity } from "../utils/teamIdentity";
import {
  formatAmericanOdds,
  formatProductDate,
  parseProductDate,
} from "../utils/productFormat";
import { SavePickButton } from "./SavePickButton";

interface ProductGameCardProps {
  predictions: Prediction[];
}

type MarketKey = "spread" | "moneyline" | "total";

const markets: Array<{ key: MarketKey; label: string }> = [
  { key: "spread", label: "Spread" },
  { key: "moneyline", label: "Moneyline" },
  { key: "total", label: "Total" },
];

function marketSelection(prediction: Prediction): string {
  const market = prediction.market.toLowerCase();
  const normalizedSelection = prediction.selection.trim().toUpperCase();

  if (["PASS", "NO_BET", "NO BET"].includes(normalizedSelection)) {
    return "NO BET";
  }

  if (market === "total") {
    const direction = normalizedSelection.match(/^(OVER|UNDER)\b/)?.[1];
    if (direction && prediction.line_value != null && Number.isFinite(prediction.line_value)) {
      return `${direction} ${prediction.line_value}`;
    }
    return prediction.display_selection;
  }

  const selectedTeam = getPredictionTeam(prediction);
  const abbreviation = selectedTeam
    ? getTeamIdentity(prediction.sport, selectedTeam).abbreviation
    : "—";

  if (market === "moneyline") {
    return abbreviation !== "—" ? abbreviation : prediction.display_selection;
  }

  if (market === "spread" && prediction.line_value != null && Number.isFinite(prediction.line_value)) {
    const line = prediction.line_value > 0
      ? `+${prediction.line_value}`
      : String(prediction.line_value);
    return abbreviation !== "—" ? `${abbreviation} ${line}` : prediction.display_selection;
  }

  return prediction.display_selection;
}

function isFootball(sport: string): boolean {
  return sport.toUpperCase() === "NFL" || sport.toUpperCase() === "NCAAF";
}

function kickoffLabel(value: string): string {
  const date = parseProductDate(value);
  if (!date) return "Kickoff time unavailable";
  return formatProductDate(value);
}

function quoteTimestamp(value: string | null): string | null {
  const date = parseProductDate(value);
  if (!date) return null;
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZone: "America/New_York",
    timeZoneName: "short",
  }).format(date);
}

function TeamScoreboard({
  game,
  team,
  side,
}: {
  game: Prediction;
  team: string;
  side: "AWAY" | "HOME";
}) {
  const identity = getTeamIdentity(game.sport, team);
  const abbreviation = identity.abbreviation === "—"
    ? team.trim().split(/\s+/).map((word) => word[0]).join("").slice(0, 4).toUpperCase()
    : identity.abbreviation;

  return (
    <Box sx={{
      display: "grid",
      gridTemplateRows: "subgrid",
      gridRow: "1 / span 3",
      gridColumn: side === "AWAY" ? 1 : 3,
      justifyItems: "center",
      alignItems: "start",
      minWidth: 0,
      textAlign: "center",
    }}>
      <Box
        aria-hidden="true"
        data-testid={`team-badge-${side.toLowerCase()}`}
        sx={{
          width: { xs: 66, sm: 78 },
          height: { xs: 66, sm: 78 },
          flex: "0 0 auto",
          display: "grid",
          placeItems: "center",
          position: "relative",
          borderRadius: "50%",
          border: "3px solid #00d4ff",
          background: "radial-gradient(circle at 50% 38%, #17344a 0%, #0b1823 72%)",
          boxShadow: "0 0 0 5px rgba(0, 212, 255, 0.13), 0 0 24px rgba(0, 212, 255, 0.24), inset 0 0 0 5px #0b1823, inset 0 0 0 7px rgba(46, 131, 179, 0.88)",
          "&::after": {
            content: '""',
            position: "absolute",
            width: 29,
            height: 6,
            bottom: 8,
            left: "50%",
            transform: "translateX(-50%)",
            borderRadius: 99,
            backgroundColor: "var(--gk-lime)",
            boxShadow: "0 0 12px rgba(164, 239, 24, 0.45)",
          },
        }}
      >
        <Typography
          component="span"
          sx={{
            color: "#edf4fa",
            fontSize: { xs: "1.35rem", sm: "1.55rem" },
            fontWeight: 900,
            letterSpacing: "-0.04em",
            textShadow: "0 2px 12px rgba(0, 0, 0, 0.55)",
          }}
        >
          {abbreviation}
        </Typography>
      </Box>
      <Typography
        component="span"
        data-testid={`team-name-${side.toLowerCase()}`}
        sx={{
          maxWidth: isFootball(game.sport) ? 120 : "100%",
          width: isFootball(game.sport) ? "100%" : undefined,
          height: isFootball(game.sport) ? "100%" : undefined,
          display: isFootball(game.sport) ? "flex" : undefined,
          alignItems: "center",
          justifyContent: "center",
          color: "#f0f4f8",
          fontSize: { xs: "0.94rem", sm: "1.02rem" },
          fontWeight: 800,
          lineHeight: 1.2,
          overflowWrap: "anywhere",
          textShadow: "0 2px 5px #03101a, 0 0 10px #03101a",
        }}
      >
        {team}
      </Typography>
      <Typography
        component="span"
        variant="caption"
        data-testid={`team-side-${side.toLowerCase()}`}
        sx={{
          color: side === "HOME" ? "var(--gk-lime)" : "#8fa7b8",
          fontSize: "0.68rem",
          fontWeight: 900,
          letterSpacing: "0.22em",
        }}
      >
        {side}
      </Typography>
    </Box>
  );
}

function MarketTile({
  market,
  prediction,
}: {
  market: (typeof markets)[number];
  prediction: Prediction | undefined;
}) {
  if (!prediction) {
    return (
      <Box
        data-testid={`market-tile-${market.key}`}
        sx={{
          minWidth: 0,
          minHeight: 82,
          px: { xs: 0.75, sm: 1.25 },
          py: 1,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          textAlign: "center",
          border: "1px solid rgba(0, 212, 255, 0.16)",
          borderRadius: "10px",
          background: "linear-gradient(155deg, rgba(16, 34, 50, 0.92), rgba(8, 22, 34, 0.95))",
        }}
      >
        <Typography variant="overline" sx={{ color: "#9eb2c2", fontSize: "0.61rem", fontWeight: 850 }}>
          {market.label}
        </Typography>
        <Typography variant="caption" color="text.secondary">No model pick</Typography>
      </Box>
    );
  }

  const quotePrice = formatAmericanOdds(prediction.american_odds);
  const quoteBook = prediction.sportsbook?.trim() || null;
  const observedAt = quoteTimestamp(prediction.odds_observed_at);
  const isNoBet = marketSelection(prediction) === "NO BET";

  return (
    <Box
      data-testid={`market-tile-${market.key}`}
      data-market={market.key}
      sx={{
        minWidth: 0,
        minHeight: { xs: 82, sm: 90 },
        px: { xs: 0.7, sm: 1.25 },
        py: 1,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        textAlign: "center",
        border: "1px solid rgba(0, 212, 255, 0.24)",
        borderRadius: "10px",
        background: "linear-gradient(155deg, rgba(17, 38, 56, 0.96), rgba(7, 20, 31, 0.98))",
        boxShadow: "inset 0 1px 0 rgba(237, 244, 250, 0.05), 0 8px 20px rgba(0, 0, 0, 0.18)",
      }}
    >
      <Typography
        variant="overline"
        sx={{
          color: "#91aabd",
          fontSize: "0.57rem",
          fontWeight: 850,
          letterSpacing: "0.2em",
          lineHeight: 1.2,
        }}
      >
        {market.label} · MODEL PICK
      </Typography>
      <Typography
        component="p"
        aria-label={`Model selection: ${prediction.display_selection}`}
        sx={{
          mt: 0.65,
          mb: 0,
          color: isNoBet ? "#a9bccb" : "#f5f7fa",
          fontSize: { xs: "0.98rem", sm: "1.25rem" },
          fontWeight: 950,
          letterSpacing: "-0.025em",
          lineHeight: 1.08,
          overflowWrap: "anywhere",
          textShadow: "0 2px 12px rgba(0, 0, 0, 0.38)",
        }}
      >
        {marketSelection(prediction)}
        {market.key === "moneyline" && quotePrice && !isNoBet ? ` ${quotePrice}` : ""}
      </Typography>
      <Typography
        component="span"
        variant="caption"
        sx={{
          mt: 0.45,
          maxWidth: "100%",
          color: quotePrice ? "#a9bccb" : "#f2b84b",
          fontSize: { xs: "0.54rem", sm: "0.61rem" },
          lineHeight: 1.15,
          overflowWrap: "anywhere",
          whiteSpace: "nowrap",
          overflow: "hidden",
          textOverflow: "ellipsis",
        }}
        title={quotePrice
          ? `Market quote: ${quotePrice}${quoteBook ? ` at ${quoteBook}` : ""}`
          : "Quoted price unavailable"}
      >
        {isNoBet
          ? "No selection"
          : quotePrice
            ? market.key === "moneyline"
              ? `Market quote · ${quoteBook ?? "book unavailable"}`
              : `Market quote ${quotePrice} · ${quoteBook ?? "book unavailable"}`
            : "Quoted price unavailable"}
      </Typography>
      <Typography
        component="span"
        variant="caption"
        sx={{
          mt: 0.2,
          color: "#8299aa",
          fontSize: { xs: "0.52rem", sm: "0.58rem" },
          lineHeight: 1.1,
          whiteSpace: "nowrap",
        }}
        aria-label={observedAt ? `Odds observed ${observedAt}` : "Quote time unavailable"}
        title={prediction.odds_observed_at
          ? `Odds observed ${formatProductDate(prediction.odds_observed_at)}`
          : "Quote time unavailable"}
      >
        {observedAt ?? "Quote time unavailable"}
      </Typography>
      {prediction.recommendation_designation ? (
        <Typography
          component="span"
          variant="caption"
          sx={{
            mt: 0.35,
            color: "#f2b84b",
            fontSize: "0.58rem",
            lineHeight: 1.2,
            overflowWrap: "anywhere",
          }}
        >
          {prediction.recommendation_designation}
        </Typography>
      ) : null}
      {!isNoBet ? (
        <Box sx={{ mt: 0.65 }}>
          <SavePickButton predictionId={prediction.prediction_id} compact />
        </Box>
      ) : null}
    </Box>
  );
}

export function ProductGameCard({ predictions }: ProductGameCardProps) {
  const orderedPredictions = [...predictions].sort(
    (left, right) => markets.findIndex(({ key }) => key === left.market.toLowerCase()) -
      markets.findIndex(({ key }) => key === right.market.toLowerCase()),
  );
  const game = orderedPredictions[0];
  if (!game) return null;

  const marketPredictions = Object.fromEntries(
    markets.map(({ key }) => [
      key,
      orderedPredictions.find((prediction) => prediction.market.toLowerCase() === key),
    ]),
  ) as Record<MarketKey, Prediction | undefined>;
  const background = isFootball(game.sport)
    ? "/game-center-football.svg"
    : "/game-center-basketball.svg";
  const analysisLabel = `View Game Analysis for ${game.away_team} at ${game.home_team}`;

  return (
    <Card
      data-testid="game-card"
      data-game-id={game.game_id}
      data-sport={game.sport}
      className="gk-card"
      sx={{
        minWidth: 0,
        height: "100%",
        overflow: "hidden",
        border: "1px solid rgba(0, 212, 255, 0.25)",
        borderRadius: { xs: "16px", md: "18px" },
        background: "linear-gradient(155deg, #0b1823 0%, #08141e 100%)",
        boxShadow: "0 18px 42px rgba(0, 0, 0, 0.36), 0 0 24px rgba(0, 212, 255, 0.055)",
      }}
    >
      <CardContent
        sx={{
          p: { xs: 1, sm: 1.25, md: 1.5 },
          "&:last-child": { pb: { xs: 1, sm: 1.25, md: 1.5 } },
        }}
      >
        <Stack spacing={{ xs: 0.85, md: 1.25 }}>
          <Box
            data-testid="game-center-matchup"
            sx={{
              minHeight: isFootball(game.sport)
                ? { xs: 214, sm: 230, md: 220 }
                : { xs: 184, sm: 210, md: 190 },
              px: { xs: 1, sm: 1.5 },
              py: 1.25,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "space-between",
              gap: isFootball(game.sport) ? 2 : undefined,
              border: "1px solid rgba(0, 212, 255, 0.20)",
              borderRadius: "13px",
              overflow: "hidden",
              backgroundImage: isFootball(game.sport)
                ? `linear-gradient(180deg, rgba(3, 12, 20, 0.3), rgba(3, 12, 20, 0.08) 52%, rgba(3, 12, 20, 0.58)), url("${background}")`
                : `linear-gradient(180deg, rgba(3, 12, 20, 0.28) 0%, rgba(3, 12, 20, 0.12) 42%, rgba(3, 12, 20, 0.5) 100%), url("${background}")`,
              backgroundSize: "cover",
              backgroundPosition: "center",
              boxShadow: "inset 0 0 32px rgba(1, 8, 14, 0.24), 0 10px 26px rgba(0, 0, 0, 0.28)",
            }}
          >
            <Stack alignItems="center" spacing={0.4}>
              <Chip
                label={game.sport}
                size="small"
                variant="outlined"
                sx={{
                  height: 22,
                  borderColor: "rgba(0, 212, 255, 0.45)",
                  color: "#d4e4ee",
                  backgroundColor: "rgba(6, 16, 25, 0.62)",
                  fontSize: "0.65rem",
                  fontWeight: 850,
                  letterSpacing: "0.14em",
                }}
              />
              <Typography
                component="time"
                dateTime={game.game_date}
                variant="body2"
                sx={{
                  color: "#eef4f8",
                  fontFamily: "var(--gk-font-mono)",
                  fontSize: { xs: "0.79rem", sm: "0.86rem" },
                  fontWeight: 800,
                  textAlign: "center",
                  textShadow: "0 2px 10px rgba(0, 0, 0, 0.7)",
                }}
              >
                {kickoffLabel(game.game_date)}
              </Typography>
            </Stack>

            <Box
              sx={{
                width: "100%",
                display: "grid",
                gridTemplateColumns: "minmax(0, 1fr) auto minmax(0, 1fr)",
                gridTemplateRows: "auto auto auto",
                columnGap: { xs: 0.6, sm: 1.5 },
                rowGap: 0.65,
              }}
            >
              <TeamScoreboard game={game} team={game.away_team} side="AWAY" />
              <Typography
                component="span"
                sx={{
                  color: "#f5f7fa",
                  gridColumn: 2,
                  gridRow: 1,
                  alignSelf: "center",
                  fontFamily: "var(--gk-font-editorial)",
                  fontSize: { xs: "1.45rem", sm: "1.8rem" },
                  fontWeight: 900,
                  textShadow: "0 0 14px rgba(0, 212, 255, 0.45)",
                }}
              >
                VS
              </Typography>
              <TeamScoreboard game={game} team={game.home_team} side="HOME" />
            </Box>
          </Box>

          <Box
            aria-label="Model selections and market quotes"
            sx={{
              display: "grid",
              gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
              gap: { xs: 0.65, sm: 1 },
            }}
          >
            {markets.map((market) => (
              <MarketTile
                key={market.key}
                market={market}
                prediction={marketPredictions[market.key]}
              />
            ))}
          </Box>

          <Button
              component={RouterLink}
              to={`/games/${game.game_id}`}
              aria-label={analysisLabel}
              data-testid="view-pick-analysis"
              variant="contained"
              startIcon={<InsightsOutlinedIcon />}
              endIcon={<ArrowForwardOutlinedIcon />}
              sx={{
                minHeight: { xs: 42, sm: 46 },
                flex: 1,
                color: "#06111b",
                background: "linear-gradient(100deg, #a4ef18 0%, #96e516 100%)",
                fontWeight: 900,
                fontSize: { xs: "0.96rem", sm: "1rem" },
                boxShadow: "0 0 22px rgba(164, 239, 24, 0.21), 0 8px 18px rgba(0, 0, 0, 0.24)",
                "&:hover": {
                  background: "linear-gradient(100deg, #b5f54a 0%, #a4ef18 100%)",
                  boxShadow: "0 0 28px rgba(164, 239, 24, 0.3), 0 10px 20px rgba(0, 0, 0, 0.28)",
                },
                "&:focus-visible": {
                  outline: "3px solid #edf4fa",
                  outlineOffset: 2,
                },
              }}
            >
              View pick analysis
          </Button>
        </Stack>
      </CardContent>
    </Card>
  );
}
