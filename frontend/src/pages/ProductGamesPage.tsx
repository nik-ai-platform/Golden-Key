import { Box, Button, Stack, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { ProductGameCard } from "../components/ProductGameCard";
import { getUpcomingPredictions } from "../services/productApi";
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

export function ProductGamesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const sport = searchParams.get("sport") || undefined;
  const query = useQuery({
    queryKey: ["product", "upcoming", sport],
    queryFn: () => getUpcomingPredictions(sport),
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
    <Stack spacing={3}>
      <Box>
        <Typography variant="h4" fontWeight={700}>
          Games
        </Typography>

        <Typography color="text.secondary" sx={{ mt: 1 }}>
          Review the next 14 days of matchups and compare Nik AI&apos;s Spread,
          Moneyline, and Total picks.
        </Typography>
      </Box>

      <Stack
        direction="row"
        spacing={1}
        flexWrap="wrap"
        useFlexGap
      >
        <Button
          variant={!sport ? "contained" : "outlined"}
          onClick={() => setSearchParams({})}
        >
          All
        </Button>

        {sports.map((item) => (
          <Button
            key={item}
            variant={sport === item ? "contained" : "outlined"}
            onClick={() => setSearchParams({ sport: item })}
          >
            {item}
          </Button>
        ))}
      </Stack>

      {sections.length ? (
        <Stack spacing={2.5}>
          {sections.map((section) => (
            <Box component="section" key={section.dateKey} aria-labelledby={`games-${section.dateKey}`}>
              <Typography id={`games-${section.dateKey}`} variant="overline" fontWeight={900}>
                {formatSectionHeading(section.dateKey)}
              </Typography>
              <Stack spacing={2.5} sx={{ mt: 1 }}>
                {section.games.map((predictions) => (
                  <ProductGameCard
                    key={predictions[0].game_id}
                    predictions={predictions}
                  />
                ))}
              </Stack>
            </Box>
          ))}
        </Stack>
      ) : (
        <EmptyState
          title="No upcoming games are currently available."
        />
      )}
    </Stack>
  );
}
