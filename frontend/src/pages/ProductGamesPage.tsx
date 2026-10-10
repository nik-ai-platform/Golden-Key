import CalendarTodayOutlinedIcon from "@mui/icons-material/CalendarTodayOutlined";
import {
  Box,
  Chip,
  Link,
  Stack,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { Link as RouterLink, useSearchParams } from "react-router-dom";

import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { ProductGameCard } from "../components/ProductGameCard";
import { getPerformance, getUpcomingPredictions } from "../services/productApi";
import type { Prediction } from "../types/product";
import { parseProductDate, productDateKey } from "../utils/productFormat";

const sports = ["NFL", "NBA", "NCAAF", "NCAAB", "WNBA"];

function addUtcDays(dateKey: string, days: number): string {
  const date = new Date(`${dateKey}T12:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

function formatSectionHeading(dateKey: string): string {
  const label = new Intl.DateTimeFormat("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${dateKey}T12:00:00Z`)).toLocaleUpperCase("en-US");
  const today = productDateKey(new Date().toISOString());

  if (dateKey === today) return `TODAY — ${label}`;
  if (today && dateKey === addUtcDays(today, 1)) return `TOMORROW — ${label}`;
  return label;
}

function recentResultLabel(result: {
  sport: string;
  market: string;
  display_selection: string;
  away_team: string;
  home_team: string;
  outcome: string;
}): string {
  return `${result.outcome} · ${result.sport} · ${result.market} · ${result.display_selection} · ${result.away_team} at ${result.home_team}`;
}

export function ProductGamesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const sport = searchParams.get("sport") || undefined;
  const query = useQuery({
    queryKey: ["product", "upcoming", sport],
    queryFn: () => getUpcomingPredictions(sport),
  });
  const performanceQuery = useQuery({
    queryKey: ["product", "performance"],
    queryFn: getPerformance,
    retry: false,
  });

  const sections = useMemo(() => {
    const grouped = new Map<number, Prediction[]>();

    for (const prediction of query.data?.predictions ?? []) {
      const existing = grouped.get(prediction.game_id) ?? [];
      existing.push(prediction);
      grouped.set(prediction.game_id, existing);
    }

    const games = Array.from(grouped.values()).sort((a, b) => {
      const aDate = parseProductDate(a[0]?.game_date)?.getTime() ?? Number.POSITIVE_INFINITY;
      const bDate = parseProductDate(b[0]?.game_date)?.getTime() ?? Number.POSITIVE_INFINITY;

      return aDate - bDate;
    });
    const byDate = new Map<string, Prediction[][]>();

    for (const game of games) {
      const dateKey = productDateKey(game[0]?.game_date);
      if (!dateKey) continue;
      byDate.set(dateKey, [...(byDate.get(dateKey) ?? []), game]);
    }

    return Array.from(byDate, ([dateKey, dateGames]) => ({ dateKey, games: dateGames }));
  }, [query.data?.predictions]);

  if (query.isLoading) {
    return <LoadingState message="Loading games..." />;
  }

  if (query.isError) {
    return (
      <ErrorState
        kind="network"
        detail="Unable to load games right now."
        onRetry={() => void query.refetch()}
      />
    );
  }

  return (
    <Stack spacing={{ xs: 1.5, md: 3 }} data-testid="game-center" sx={{ position: "relative" }}>
      <Box sx={{ textAlign: "center", pt: { xs: 0.25, md: 1 } }}>
        <Typography
          component="p"
          variant="overline"
          sx={{
            mb: 0.25,
            color: "var(--gk-cyan)",
            fontSize: "0.61rem",
            letterSpacing: "0.24em",
          }}
        >
          BEAR A HAND SPORTS · MATCH CENTER
        </Typography>
        <Typography
          className="gk-editorial"
          component="h1"
          variant="h3"
          fontWeight={850}
          sx={{ fontSize: { xs: "2.25rem", sm: "2.65rem" }, lineHeight: 1.04 }}
        >
          Game Center
        </Typography>
        <Typography
          color="text.secondary"
          sx={{ mt: 0.5, fontSize: { xs: "0.95rem", md: "1.05rem" } }}
        >
          Your slate. Your perspective.
        </Typography>
      </Box>

      <Stack spacing={{ xs: 0.65, md: 1.25 }}>
        <Stack
          direction="row"
          spacing={{ xs: 0.35, md: 0.75 }}
          flexWrap={{ xs: "nowrap", md: "wrap" }}
          justifyContent="center"
          aria-label="Filter games by sport"
          sx={{ maxWidth: "100%", overflowX: { xs: "auto", md: "visible" }, pb: 0.25 }}
        >
          <Chip
            label="All"
            size="small"
            clickable
            aria-pressed={!sport}
            data-testid="sport-filter-all"
            onClick={() => setSearchParams({})}
            sx={{
              height: { xs: 28, md: 32 },
              color: !sport ? "#06111b" : "#b6c6d3",
              fontSize: { xs: "0.67rem", md: "0.8125rem" },
              fontWeight: 800,
              backgroundColor: !sport ? "var(--gk-lime)" : "rgba(11, 24, 35, 0.86)",
              border: "1px solid rgba(0, 212, 255, 0.22)",
              "& .MuiChip-label": { px: { xs: 0.85, md: 1.5 } },
              "&:hover": { backgroundColor: "rgba(0, 212, 255, 0.14)" },
            }}
          />
          {sports.map((item) => (
            <Chip
              key={item}
              label={item}
              size="small"
              clickable
              aria-pressed={sport === item}
              data-testid={`sport-filter-${item.toLowerCase()}`}
              onClick={() => setSearchParams({ sport: item })}
              sx={{
                height: { xs: 28, md: 32 },
                color: sport === item ? "#06111b" : "#b6c6d3",
                fontSize: { xs: "0.67rem", md: "0.8125rem" },
                fontWeight: 800,
                backgroundColor: sport === item ? "var(--gk-lime)" : "rgba(11, 24, 35, 0.86)",
                border: "1px solid rgba(0, 212, 255, 0.22)",
                "& .MuiChip-label": { px: { xs: 0.85, md: 1.5 } },
                "&:hover": { backgroundColor: sport === item ? "#b5f54a" : "rgba(0, 212, 255, 0.14)" },
              }}
            />
          ))}
        </Stack>
      </Stack>

      {sections.length ? (
        <Stack spacing={{ xs: 2.25, md: 3 }}>
          {sections.map((section) => (
            <Box component="section" key={section.dateKey} aria-labelledby={`games-${section.dateKey}`}>
              <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1.25 }}>
                <CalendarTodayOutlinedIcon sx={{ color: "var(--gk-cyan)", fontSize: 17 }} />
                <Typography
                  id={`games-${section.dateKey}`}
                  component="h2"
                  variant="overline"
                  fontWeight={900}
                  sx={{ color: "#b9c8d3", letterSpacing: "0.16em" }}
                >
                  {formatSectionHeading(section.dateKey)}
                </Typography>
                <Box sx={{ flex: 1, height: "1px", background: "rgba(0, 212, 255, 0.17)" }} />
              </Stack>
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: { xs: "minmax(0, 1fr)", md: "repeat(2, minmax(0, 1fr))" },
                  gap: { xs: 1.75, md: 2.25 },
                  alignItems: "stretch",
                }}
              >
                {section.games.map((predictions) => (
                  <ProductGameCard
                    key={predictions[0].game_id}
                    predictions={predictions}
                  />
                ))}
              </Box>
            </Box>
          ))}
        </Stack>
      ) : (
        <EmptyState title="No upcoming games are currently available." />
      )}

      <Box
        component="section"
        aria-labelledby="recent-model-results-heading"
        data-testid="recent-model-results"
        sx={{
          mt: { xs: 0.5, md: 1 },
          pt: 1.5,
          borderTop: "1px solid rgba(0, 212, 255, 0.2)",
        }}
      >
        <Stack direction="row" alignItems="baseline" justifyContent="space-between" spacing={1} sx={{ mb: 1.1 }}>
          <Typography
            id="recent-model-results-heading"
            component="h2"
            variant="h6"
            fontWeight={850}
            sx={{ fontSize: { xs: "1.08rem", sm: "1.25rem" } }}
          >
            Recent model results
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ flexShrink: 0 }}>
            Settled picks
          </Typography>
        </Stack>
        {performanceQuery.isLoading ? (
          <Typography variant="caption" color="text.secondary">Loading settled results…</Typography>
        ) : performanceQuery.isError ? (
          <Typography role="status" variant="caption" color="warning.main">
            Recent settled results are temporarily unavailable.
          </Typography>
        ) : performanceQuery.data?.recent_results.length ? (
          <Stack
            direction="row"
            spacing={0.75}
            sx={{
              overflowX: "auto",
              py: 0.5,
              px: 0.15,
              scrollbarWidth: "thin",
              "&::-webkit-scrollbar": { height: 5 },
              "&::-webkit-scrollbar-thumb": { backgroundColor: "rgba(0, 212, 255, 0.28)", borderRadius: 99 },
            }}
          >
            {performanceQuery.data.recent_results.slice(0, 10).map((result) => {
              const color = result.outcome === "WIN"
                ? { foreground: "#a4ef18", border: "rgba(164, 239, 24, 0.52)", glow: "rgba(164, 239, 24, 0.11)" }
                : result.outcome === "LOSS"
                  ? { foreground: "#ff7880", border: "rgba(240, 93, 104, 0.52)", glow: "rgba(240, 93, 104, 0.1)" }
                  : { foreground: "#afc2d0", border: "rgba(92, 128, 154, 0.52)", glow: "rgba(0, 212, 255, 0.06)" };
              return (
                <Chip
                  key={result.prediction_id}
                  component={RouterLink}
                  to={`/games/${result.game_id}`}
                  label={result.outcome}
                  aria-label={recentResultLabel(result)}
                  data-testid="recent-model-result"
                  sx={{
                    minWidth: 62,
                    height: 36,
                    flexShrink: 0,
                    color: color.foreground,
                    border: `1px solid ${color.border}`,
                    borderRadius: "9px",
                    backgroundColor: color.glow,
                    fontFamily: "var(--gk-font-mono)",
                    fontSize: "0.68rem",
                    fontWeight: 900,
                    "&:hover": { backgroundColor: color.glow, filter: "brightness(1.25)" },
                    "&:focus-visible": { outline: "2px solid var(--gk-cyan)", outlineOffset: 2 },
                  }}
                />
              );
            })}
          </Stack>
        ) : (
          <Stack spacing={0.5}>
            <Typography variant="body2" color="text.secondary">
              No recent settled model picks.
            </Typography>
            <Link component={RouterLink} to="/performance" variant="caption" sx={{ alignSelf: "flex-start" }}>
              View performance history
            </Link>
          </Stack>
        )}
      </Box>
    </Stack>
  );
}
