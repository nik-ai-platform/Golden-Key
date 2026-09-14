import { Box, Stack, Typography } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";

import { NEUTRAL_TEAM_IDENTITY } from "../data/teamIdentity";
import type { Prediction } from "../types/product";
import { formatAmericanOdds, formatProductTime, parseProductDate } from "../utils/productFormat";
import { getPredictionTeam, getTeamIdentity } from "../utils/teamIdentity";
import { TeamAccent } from "./TeamAccent";

const MARKET_KEYS = ["spread", "moneyline", "total"] as const;
type MarketKey = (typeof MARKET_KEYS)[number];

interface SportsbookGamesBoardProps {
  predictions: Prediction[];
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
        fontSize="0.78rem"
        fontWeight={recommended ? 900 : 700}
        sx={{ overflowWrap: "anywhere" }}
      >
        {marketValue(prediction, market)}
      </Typography>
    </Box>
  );
}

function TeamRow({ prediction, team }: { prediction: Prediction; team: string }) {
  return (
    <Stack direction="row" alignItems="center" spacing={1} sx={{ minHeight: 31, minWidth: 0 }}>
      <TeamAccent identity={getTeamIdentity(prediction.sport, team)} variant="bar" />
      <Typography fontWeight={750} fontSize="0.84rem" sx={{ overflowWrap: "anywhere" }}>{team}</Typography>
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
  game: Prediction;
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
        gridTemplateColumns: "minmax(0, 1fr) minmax(42px, auto) minmax(70px, auto) minmax(70px, auto)",
        alignItems: "center",
        columnGap: 0.5,
        minWidth: 0,
      }}
    >
      <TeamRow prediction={game} team={team} />
      <Typography data-testid={`game-${game.game_id}-${side}-score`} fontFamily="var(--gk-font-mono)" fontSize="0.78rem" fontWeight={700} textAlign="center">
        —
      </Typography>
      <MarketValue
        gameId={game.game_id}
        market="spread"
        prediction={spread}
        recommended={Boolean(spread && recommendedPredictionIds.has(spread.prediction_id))}
      />
      <MarketValue
        gameId={game.game_id}
        market="moneyline"
        prediction={moneyline}
        recommended={Boolean(moneyline && recommendedPredictionIds.has(moneyline.prediction_id))}
      />
    </Box>
  );
}

export function SportsbookGamesBoard({ predictions, recommendedPredictionIds, maxGames }: SportsbookGamesBoardProps) {
  const games = [...predictions]
    .reduce<Map<number, Prediction[]>>((grouped, prediction) => {
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
    <Box data-testid="sportsbook-games-board" sx={{ borderTop: "1px solid var(--gk-border-strong)" }}>
      <Box
        sx={{
          display: { xs: "none", md: "grid" },
          gridTemplateColumns: "90px minmax(220px, 1.6fr) minmax(125px, 0.75fr) minmax(115px, 0.7fr) minmax(125px, 0.75fr)",
          gap: 1.5,
          px: 1.5,
          py: 0.8,
          borderBottom: "1px solid var(--gk-border-strong)",
          backgroundColor: "rgba(0, 0, 0, 0.24)",
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
              gridTemplateColumns: { md: "90px minmax(220px, 1.6fr) minmax(125px, 0.75fr) minmax(115px, 0.7fr) minmax(125px, 0.75fr)" },
              gap: { md: 1.5 },
              px: { xs: 1.25, md: 1.5 },
              py: { xs: 1.5, md: 1 },
              borderBottom: "1px solid var(--gk-border)",
              transition: "background-color 140ms ease",
              "@media (hover: hover)": { "&:hover": { backgroundColor: "rgba(255, 255, 255, 0.025)" } },
            }}
          >
            <Typography color="text.secondary" fontFamily="var(--gk-font-mono)" fontSize="0.76rem" fontWeight={800} sx={{ pt: { md: 0.75 }, mb: { xs: 1, md: 0 } }}>
              {formatProductTime(game.game_date)}
            </Typography>

            <Box
              component={RouterLink}
              to={`/games/${game.game_id}`}
              aria-label={`View analysis for ${game.away_team} at ${game.home_team}`}
              sx={{
                mb: { xs: 1.25, md: 0 },
                color: "inherit",
                textDecoration: "none",
                borderRadius: 1,
                "&:hover .MuiTypography-root": { color: "var(--gk-gold-bright)" },
                "&:focus-visible": { outline: "2px solid var(--gk-gold)", outlineOffset: 2 },
              }}
            >
              <Stack spacing={0.25} sx={{ display: { xs: "none", md: "flex" } }}>
                <TeamRow prediction={game} team={game.away_team} />
                <TeamRow prediction={game} team={game.home_team} />
              </Stack>
              <Box sx={{ display: { xs: "block", md: "none" }, minWidth: 0 }}>
              <Box
                aria-hidden="true"
                sx={{
                  display: "grid",
                  gridTemplateColumns: "minmax(0, 1fr) minmax(42px, auto) minmax(70px, auto) minmax(70px, auto)",
                  columnGap: 0.5,
                  mb: 0.25,
                }}
              >
                {['Team', 'Score', 'Spread', 'Moneyline'].map((label) => (
                  <Typography key={label} variant="caption" color="text.secondary" fontWeight={850} textAlign={label === "Team" ? "left" : "center"} textTransform="uppercase">
                    {label}
                  </Typography>
                ))}
              </Box>
              <Stack spacing={0.25} sx={{ minWidth: 0 }}>
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
              </Box>
            </Box>

            <Box
                data-testid={`game-${game.game_id}-total-row`}
                sx={{
                  display: { xs: "grid", md: "none" },
                  gridTemplateColumns: "minmax(0, 1fr) minmax(140px, auto)",
                  alignItems: "center",
                  gap: 1,
                  mt: 0.75,
                  pt: 0.75,
                  borderTop: "1px solid var(--gk-border)",
                  minWidth: 0,
                }}
              >
                <Typography variant="caption" color="text.secondary" fontWeight={850} textTransform="uppercase">
                  Game total
                </Typography>
                <MarketValue
                  gameId={game.game_id}
                  market="total"
                  prediction={markets.total}
                  recommended={Boolean(markets.total && recommendedPredictionIds.has(markets.total.prediction_id))}
                />
            </Box>

            <Box sx={{ display: { xs: "none", md: "contents" } }}>
              {MARKET_KEYS.map((market, marketIndex) => (
                <Box key={market} sx={{ minWidth: 0 }}>
                  <Stack spacing={0.25}>
                    <MarketValue
                      gameId={game.game_id}
                      market={market}
                      prediction={awayMarkets[marketIndex]}
                      recommended={Boolean(awayMarkets[marketIndex] && recommendedPredictionIds.has(awayMarkets[marketIndex]!.prediction_id))}
                    />
                    {market === "total" ? (
                      <Box sx={{ minHeight: 31 }} />
                    ) : (
                      <MarketValue
                        gameId={game.game_id}
                        market={market}
                        prediction={homeMarkets[marketIndex]}
                        recommended={Boolean(homeMarkets[marketIndex] && recommendedPredictionIds.has(homeMarkets[marketIndex]!.prediction_id))}
                      />
                    )}
                  </Stack>
                </Box>
              ))}
            </Box>
          </Box>
        );
      })}
    </Box>
  );
}