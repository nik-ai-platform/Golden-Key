import { Box, Stack, Typography } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";

import { NEUTRAL_TEAM_IDENTITY } from "../data/teamIdentity";
import type { GameDetail, Prediction } from "../types/product";
import { formatAmericanOdds, formatProductTime, parseProductDate } from "../utils/productFormat";
import { getPredictionTeam, getTeamIdentity } from "../utils/teamIdentity";
import { TeamAccent } from "./TeamAccent";

const MARKET_KEYS = ["spread", "moneyline", "total"] as const;
type MarketKey = (typeof MARKET_KEYS)[number];
type BoardPrediction = Prediction & Partial<Pick<GameDetail, "home_score" | "away_score">>;

interface SportsbookGamesBoardProps {
  predictions: BoardPrediction[];
  recommendedPredictionIds: Set<number>;
  maxGames?: number;
}

function formatLine(value: number): string {
  return `${value > 0 ? "+" : ""}${value}`;
}

function marketValue(prediction: Prediction | undefined, market: MarketKey): string {
  if (!prediction) return "—";

  const odds = prediction.american_odds == null
    ? null
    : formatAmericanOdds(prediction.american_odds);

  if (market === "moneyline") return odds ?? "—";
  if (prediction.line_value == null) return odds ?? "—";

  const line = formatLine(prediction.line_value);
  if (market === "spread") return odds ? `${line}  ${odds}` : line;

  const selection = prediction.selection.trim().toLocaleUpperCase("en-US");
  const direction = selection.startsWith("OVER") ? "O" : selection.startsWith("UNDER") ? "U" : "";
  const total = direction ? `${direction} ${prediction.line_value}` : `${prediction.line_value}`;
  return odds ? `${total}  ${odds}` : total;
}

function sameTeam(prediction: Prediction, team: string): boolean {
  const selectedTeam = getPredictionTeam(prediction);
  if (!selectedTeam) return false;

  const normalize = (value: string) => value.trim().replace(/\s+/g, " ").toLocaleLowerCase("en-US");
  if (normalize(selectedTeam) === normalize(team)) return true;

  const selectedIdentity = getTeamIdentity(prediction.sport, selectedTeam);
  const rowIdentity = getTeamIdentity(prediction.sport, team);
  return selectedIdentity !== NEUTRAL_TEAM_IDENTITY && selectedIdentity === rowIdentity;
}

function MarketValue({
  gameId,
  market,
  prediction,
  recommended,
}: {
  gameId: number;
  market: MarketKey;
  prediction?: Prediction;
  recommended: boolean;
}) {
  return (
    <Box
      data-testid={`game-${gameId}-${market}-value`}
      data-recommended={recommended ? "true" : "false"}
      aria-label={recommended ? `${market} Bear A Hand Sports recommendation` : undefined}
      sx={{
        minHeight: 31,
        px: 1,
        display: "flex",
        alignItems: "center",
        border: "1px solid",
        borderColor: recommended ? "rgba(214, 173, 69, 0.72)" : "transparent",
        backgroundColor: recommended ? "rgba(214, 173, 69, 0.09)" : "transparent",
        color: recommended ? "var(--gk-gold-bright)" : "text.primary",
      }}
    >
      <Typography
        component="span"
        fontFamily="var(--gk-font-mono)"
        fontWeight={recommended ? 900 : 700}
        sx={{ overflowWrap: "anywhere", fontSize: { xs: "0.78rem", md: "0.84rem" } }}
      >
        {marketValue(prediction, market)}
      </Typography>
    </Box>
  );
}

function TeamRow({ prediction, team, score }: { prediction: Prediction; team: string; score?: number | null }) {
  return (
    <Stack direction="row" alignItems="center" spacing={1} sx={{ minHeight: { xs: 28, md: 31 }, minWidth: 0 }}>
      <TeamAccent identity={getTeamIdentity(prediction.sport, team)} variant="bar" />
      <Typography fontWeight={750} sx={{ overflowWrap: "anywhere", fontSize: { xs: "0.84rem", md: "0.9rem" } }}>{team}</Typography>
      {score != null ? <Typography fontFamily="var(--gk-font-mono)" fontWeight={700}>{score}</Typography> : null}
    </Stack>
  );
}

function MobileTeamRow({
  game,
  side,
  team,
  spread,
  moneyline,
  recommendedPredictionIds,
}: {
  game: BoardPrediction;
  side: "away" | "home";
  team: string;
  spread?: Prediction;
  moneyline?: Prediction;
  recommendedPredictionIds: Set<number>;
}) {
  return (
    <Box
      data-testid={`game-${game.game_id}-${side}-team-row`}
      sx={{
        display: "grid",
        gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
        gap: 0.125,
        py: 0.375,
        minWidth: 0,
      }}
    >
      <Stack direction="row" alignItems="center" justifyContent="space-between" spacing={1} sx={{ gridColumn: "1 / -1" }}>
        <TeamRow prediction={game} team={team} />
        <Typography data-testid={`game-${game.game_id}-${side}-score`} aria-label={`${team} score`} fontFamily="var(--gk-font-mono)" fontSize="0.78rem" fontWeight={700}>
          {game[`${side}_score`] ?? "—"}
        </Typography>
      </Stack>
      <Stack direction="row" alignItems="center" spacing={0.25}>
        <Typography variant="caption" color="text.secondary">Spread</Typography>
        <MarketValue
          gameId={game.game_id}
          market="spread"
          prediction={spread}
          recommended={Boolean(spread && recommendedPredictionIds.has(spread.prediction_id))}
        />
      </Stack>
      <Stack direction="row" alignItems="center" spacing={0.25}>
        <Typography variant="caption" color="text.secondary">Moneyline</Typography>
        <MarketValue
          gameId={game.game_id}
          market="moneyline"
          prediction={moneyline}
          recommended={Boolean(moneyline && recommendedPredictionIds.has(moneyline.prediction_id))}
        />
      </Stack>
    </Box>
  );
}

export function SportsbookGamesBoard({ predictions, recommendedPredictionIds, maxGames }: SportsbookGamesBoardProps) {
  const games = [...predictions]
    .reduce<Map<number, BoardPrediction[]>>((grouped, prediction) => {
      grouped.set(prediction.game_id, [...(grouped.get(prediction.game_id) ?? []), prediction]);
      return grouped;
    }, new Map())
    .values();
  const orderedGames = [...games].sort(
    (left, right) =>
      (parseProductDate(left[0].game_date)?.getTime() ?? Number.POSITIVE_INFINITY) -
      (parseProductDate(right[0].game_date)?.getTime() ?? Number.POSITIVE_INFINITY),
  ).slice(0, maxGames);

  return (
    <Box data-testid="sportsbook-games-board" sx={{ borderTop: { md: "1px solid var(--gk-border-strong)" } }}>
      <Box
        sx={{
          display: { xs: "none", md: "grid" },
          gridTemplateColumns: "64px minmax(140px, 1.6fr) repeat(3, minmax(100px, 0.75fr))",
          gap: 1.5,
          px: 1.5,
          py: 1.25,
          borderBottom: "1px solid var(--gk-border-strong)",
          backgroundColor: "var(--gk-surface-soft)",
        }}
      >
        {['Time', 'Matchup', 'Spread', 'Moneyline', 'Total'].map((label) => (
          <Typography key={label} variant="caption" color="text.secondary" fontWeight={850} textTransform="uppercase">
            {label}
          </Typography>
        ))}
      </Box>

      {orderedGames.map((gamePredictions) => {
        const game = gamePredictions[0];
        const markets = Object.fromEntries(
          MARKET_KEYS.map((market) => {
            const candidates = gamePredictions.filter((prediction) => prediction.market.toLowerCase() === market);
            return [market, candidates.find((prediction) => recommendedPredictionIds.has(prediction.prediction_id)) ?? candidates[0]];
          }),
        ) as Record<MarketKey, Prediction | undefined>;
        const teamMarkets = (team: string) => MARKET_KEYS.map((market) => {
          const prediction = markets[market];
          return market === "total" || (prediction && sameTeam(prediction, team)) ? prediction : undefined;
        });
        const awayMarkets = teamMarkets(game.away_team);
        const homeMarkets = teamMarkets(game.home_team);

        return (
          <Box
            key={game.game_id}
            data-testid="sportsbook-game"
            data-game-id={game.game_id}
            sx={{
              display: { md: "grid" },
              gridTemplateColumns: { md: "64px minmax(140px, 1.6fr) repeat(3, minmax(100px, 0.75fr))" },
              gap: { md: 1.5 },
              px: { xs: 1.25, md: 1.5 },
              py: { xs: 0.75, md: 1.5 },
              mb: { xs: 1.5, md: 0 },
              border: { xs: "1px solid var(--gk-border-strong)", md: 0 },
              borderRadius: { xs: "var(--gk-radius-sm)", md: 0 },
              backgroundColor: "var(--gk-surface)",
              borderBottom: "1px solid var(--gk-border-strong)",
              "&:nth-of-type(odd)": { backgroundColor: { md: "action.hover" } },
              transition: "background-color 140ms ease",
              "@media (hover: hover)": { "&:hover": { backgroundColor: "rgba(255, 255, 255, 0.025)" } },
            }}
          >
            <Box
              data-testid={`game-${game.game_id}-header`}
              sx={{ display: { xs: "flex", md: "contents" }, alignItems: "center", justifyContent: "space-between", gap: 1 }}
            >
              <Typography color="text.secondary" fontFamily="var(--gk-font-mono)" fontWeight={800} sx={{ pt: { md: 0.75 }, fontSize: { xs: "0.76rem", md: "0.82rem" } }}>
                {formatProductTime(game.game_date)}
              </Typography>

              <Box
                component={RouterLink}
                to={`/games/${game.game_id}`}
                aria-label={`View analysis for ${game.away_team} at ${game.home_team}`}
                sx={{
                  display: "flex",
                  alignItems: "center",
                  minHeight: 44,
                  minWidth: 44,
                  flexShrink: 0,
                  color: "inherit",
                  textDecoration: "none",
                  borderRadius: 1,
                  "&:hover .MuiTypography-root": { color: "var(--gk-gold-bright)" },
                  "&:focus-visible": { outline: "2px solid var(--gk-gold)", outlineOffset: 2 },
                }}
              >
                <Stack spacing={0.25} sx={{ display: { xs: "none", md: "flex" } }}>
                  <TeamRow prediction={game} team={game.away_team} score={game.away_score} />
                  <TeamRow prediction={game} team={game.home_team} score={game.home_score} />
                </Stack>
                <Typography variant="caption" color="primary.main" sx={{ display: { xs: "block", md: "none" }, textDecoration: "underline", textUnderlineOffset: "3px" }}>
                  View matchup analysis
                </Typography>
              </Box>
            </Box>
            <Stack divider={<Box sx={{ borderTop: "1px solid var(--gk-border)" }} />} sx={{ display: { xs: "flex", md: "none" }, minWidth: 0 }}>
              <MobileTeamRow
                game={game}
                side="away"
                team={game.away_team}
                spread={awayMarkets[0]}
                moneyline={awayMarkets[1]}
                recommendedPredictionIds={recommendedPredictionIds}
              />
              <MobileTeamRow
                game={game}
                side="home"
                team={game.home_team}
                spread={homeMarkets[0]}
                moneyline={homeMarkets[1]}
                recommendedPredictionIds={recommendedPredictionIds}
              />
            </Stack>
            <Box sx={{ display: { xs: "none", md: "contents" } }}>
              {(["spread", "moneyline"] as const).map((market, marketIndex) => (
                <Box key={market} sx={{ minWidth: 0, gridColumn: marketIndex + 3, gridRow: 1 }}>
                  <Stack spacing={0.25}>
                    <MarketValue
                      gameId={game.game_id}
                      market={market}
                      prediction={awayMarkets[marketIndex]}
                      recommended={Boolean(awayMarkets[marketIndex] && recommendedPredictionIds.has(awayMarkets[marketIndex]!.prediction_id))}
                    />
                    <MarketValue
                      gameId={game.game_id}
                      market={market}
                      prediction={homeMarkets[marketIndex]}
                      recommended={Boolean(homeMarkets[marketIndex] && recommendedPredictionIds.has(homeMarkets[marketIndex]!.prediction_id))}
                    />
                  </Stack>
                </Box>
              ))}
            </Box>
            <Box
              data-testid={`game-${game.game_id}-total-row`}
              sx={{
                display: "grid",
                gridTemplateColumns: { xs: "minmax(0, 1fr) auto", md: "minmax(0, 1fr)" },
                alignItems: "center",
                gap: 1,
                gridColumn: { md: 5 },
                gridRow: { md: 1 },
                alignSelf: { md: "start" },
                mt: { xs: 0.5, md: 0 },
                pt: { xs: 0.5, md: 0 },
                borderTop: { xs: "1px solid var(--gk-border)", md: 0 },
                minWidth: 0,
              }}
            >
              <Typography variant="caption" color="text.secondary" fontWeight={850} textTransform="uppercase" sx={{ display: { md: "none" } }}>
                Game total
              </Typography>
              <MarketValue
                gameId={game.game_id}
                market="total"
                prediction={markets.total}
                recommended={Boolean(markets.total && recommendedPredictionIds.has(markets.total.prediction_id))}
              />
            </Box>
          </Box>
        );
      })}
    </Box>
  );
}