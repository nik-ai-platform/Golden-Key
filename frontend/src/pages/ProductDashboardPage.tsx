import {
  Box,
  Grid2 as Grid,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { DailyCardPickCard } from "../components/DailyCardPickCard";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { getDailyCard } from "../services/productApi";

const SPORTS = ["NFL", "NBA", "NCAAF", "NCAAB", "WNBA"] as const;
type SportFilter = "All" | (typeof SPORTS)[number];

function slateLabel(slateDate: string): string {
  const today = new Date().toISOString().slice(0, 10);
  if (slateDate === today) return "Today's Card";
  return `Next Slate — ${new Date(`${slateDate}T00:00:00Z`).toLocaleDateString(undefined, {
    month: "long",
    day: "numeric",
    timeZone: "UTC",
  })}`;
}

export function ProductDashboardPage() {
  const [sport, setSport] = useState<SportFilter>("All");
  const query = useQuery({
    queryKey: ["product", "daily-card", sport],
    queryFn: () => getDailyCard(sport === "All" ? undefined : sport),
  });

  if (query.isLoading) {
    return <LoadingState message="Building today's card..." />;
  }

  if (query.isError) {
    return (
      <ErrorState
        kind="network"
        detail="Unable to load today's card right now."
        onRetry={() => void query.refetch()}
      />
    );
  }

  const card = query.data;

  return (
    <Stack spacing={4}>
      <Stack spacing={2}>
        <Box>
          <Typography variant="h4" fontWeight={700}>
            Golden Key {card ? slateLabel(card.slate_date) : "Card"}
          </Typography>
          <Typography color="text.secondary" sx={{ mt: 0.75 }}>
            A disciplined cross-market card ranked by model strength, confidence, simulation, and
            edge.
          </Typography>
        </Box>

        <ToggleButtonGroup
          exclusive
          value={sport}
          onChange={(_, value: SportFilter | null) => {
            if (value) setSport(value);
          }}
          size="small"
          aria-label="Filter daily card by sport"
          sx={{ alignSelf: "flex-start", flexWrap: "wrap" }}
        >
          <ToggleButton value="All">All</ToggleButton>
          {SPORTS.map((item) => (
            <ToggleButton key={item} value={item}>
              {item}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
      </Stack>

      {!card || card.count === 0 ? (
        <EmptyState title="No upcoming predictions are currently available." />
      ) : (
        <>
          {card.best_bet ? (
            <Box component="section" aria-labelledby="best-bet-heading">
              <Typography id="best-bet-heading" variant="h5" fontWeight={800} sx={{ mb: 2 }}>
                Best Bet
              </Typography>
              <DailyCardPickCard pick={card.best_bet} prominent />
            </Box>
          ) : null}

          {card.featured_picks.length > 0 ? (
            <Box component="section" aria-labelledby="card-markets-heading">
              <Typography id="card-markets-heading" variant="h5" fontWeight={800} sx={{ mb: 2 }}>
                {slateLabel(card.slate_date)}
              </Typography>
              <Grid container spacing={2}>
                {card.featured_picks.map((pick) => (
                  <Grid key={pick.role} size={{ xs: 12, md: 6, xl: 3 }}>
                    <DailyCardPickCard pick={pick} />
                  </Grid>
                ))}
              </Grid>
            </Box>
          ) : null}

          {card.next_best.length > 0 ? (
            <Box component="section" aria-labelledby="next-best-heading">
              <Typography id="next-best-heading" variant="h5" fontWeight={800} sx={{ mb: 2 }}>
                Next Best Picks
              </Typography>
              <Grid container spacing={2}>
                {card.next_best.map((pick, index) => (
                  <Grid key={pick.prediction.prediction_id} size={{ xs: 12, lg: 4 }}>
                    <Box data-testid="next-best-pick" sx={{ height: "100%" }}>
                      <Typography variant="overline" color="text.secondary" fontWeight={800}>
                        #{index + 1}
                      </Typography>
                      <DailyCardPickCard pick={pick} />
                    </Box>
                  </Grid>
                ))}
              </Grid>
            </Box>
          ) : null}
        </>
      )}
    </Stack>
  );
}
