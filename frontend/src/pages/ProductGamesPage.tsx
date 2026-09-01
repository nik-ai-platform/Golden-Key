import { Box, Button, Stack, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";

import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { ProductGameCard } from "../components/ProductGameCard";
import { getTodayPredictions } from "../services/productApi";
import type { Prediction } from "../types/product";

const sports = ["NFL", "NBA", "NCAAF", "NCAAB", "WNBA"];

function formatSlateDate(slateDate: string): string {
  return new Date(`${slateDate}T00:00:00Z`).toLocaleDateString(undefined, {
    month: "long",
    day: "numeric",
    timeZone: "UTC",
  });
}

export function ProductGamesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const sport = searchParams.get("sport") || undefined;
  const query = useQuery({
    queryKey: ["product", "today", sport],
    queryFn: () => getTodayPredictions(sport),
  });

  const games = useMemo(() => {
    const grouped = new Map<number, Prediction[]>();

    for (const prediction of query.data?.predictions ?? []) {
      const existing = grouped.get(prediction.game_id) ?? [];
      existing.push(prediction);
      grouped.set(prediction.game_id, existing);
    }

    return Array.from(grouped.values()).sort((a, b) => {
      const aDate = new Date(a[0]?.game_date ?? 0).getTime();
      const bDate = new Date(b[0]?.game_date ?? 0).getTime();

      return aDate - bDate;
    });
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

        {query.data ? (
          <Typography variant="h6" sx={{ mt: 1 }}>
            {formatSlateDate(query.data.slate_date)}
          </Typography>
        ) : null}

        <Typography color="text.secondary" sx={{ mt: 1 }}>
          Select a sport, review the matchup, and compare Nik AI&apos;s Spread,
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

      {games.length ? (
        <Stack spacing={2.5}>
          {games.map((predictions) => (
            <ProductGameCard
              key={predictions[0].game_id}
              predictions={predictions}
            />
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
