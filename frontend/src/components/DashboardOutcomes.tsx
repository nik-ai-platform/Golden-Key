import { Box, Button, Chip, Divider, Stack, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { Link as RouterLink } from "react-router-dom";

import { getPerformance } from "../services/productApi";
import { EmptyState } from "./EmptyState";
import { ErrorState } from "./ErrorState";
import { LoadingState } from "./LoadingState";

export function DashboardOutcomes() {
  const query = useQuery({ queryKey: ["product", "performance"], queryFn: getPerformance });
  return (
    <Box component="aside" aria-labelledby="dashboard-outcomes-heading" sx={{ p: { xs: 1.5, sm: 2 }, border: "1px solid var(--gk-border-strong)", borderRadius: "var(--gk-radius-sm)", backgroundColor: "var(--gk-surface)", alignSelf: "start", minWidth: 0, overflowWrap: "anywhere" }}>
      <Stack spacing={{ xs: 1.25, sm: 2 }}>
        <Box>
          <Typography variant="overline" color="primary.main">The record, not the hype</Typography>
          <Typography component="h2" variant="h6" id="dashboard-outcomes-heading" fontWeight={800}>Model Outcomes</Typography>
          <Typography variant="caption" color="text.secondary">Settled model picks, not personal wager returns.</Typography>
        </Box>
        {query.isLoading ? <LoadingState message="Loading model outcomes..." /> : query.isError ? (
          <ErrorState kind="network" detail="Unable to load model outcomes." onRetry={() => void query.refetch()} />
        ) : !query.data ? <EmptyState title="Model outcomes are unavailable." /> : (
          <>
            <Box sx={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 1 }}>
              {[
                { label: "Wins", value: query.data.wins, color: "success.main" },
                { label: "Losses", value: query.data.losses, color: "error.main" },
                { label: "Pushes", value: query.data.pushes, color: "text.primary" },
              ].map(({ label, value, color }) => (
                <Box key={label} sx={{ p: 1, minWidth: 0, border: "1px solid var(--gk-border)", borderRadius: 1 }}>
                  <Typography className="gk-data" color={color} fontSize="1.5rem" fontWeight={700}>{value}</Typography>
                  <Typography variant="caption" color="text.secondary">{label}</Typography>
                </Box>
              ))}
            </Box>
            <Divider />
            <Typography variant="overline">Recent results</Typography>
            {query.data.recent_results.length === 0 ? <EmptyState title="No recent settled picks." /> : (
              <Stack spacing={{ xs: 1, sm: 1.5 }}>
                {query.data.recent_results.slice(0, 5).map((result) => (
                  <Box key={result.prediction_id} data-testid="dashboard-recent-result" sx={{ pb: { xs: 1, sm: 1.5 }, minWidth: 0, borderBottom: "1px solid var(--gk-border)" }}>
                    <Stack direction="row" justifyContent="space-between" spacing={1} alignItems="center">
                      <Typography variant="caption" color="text.secondary">{result.sport} · {result.market}</Typography>
                      <Chip label={result.outcome} size="small" variant="outlined" sx={{ flexShrink: 0 }} color={result.outcome === "WIN" ? "success" : result.outcome === "LOSS" ? "error" : "default"} />
                    </Stack>
                    <Typography component={RouterLink} to={`/games/${result.game_id}`} variant="body2" sx={{ display: "block", mt: 0.75, color: "text.primary", textUnderlineOffset: "3px", overflowWrap: "anywhere", "&:focus-visible": { outline: "2px solid var(--gk-cyan)" } }}>
                      {result.display_selection}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">{result.away_team} @ {result.home_team}</Typography>
                  </Box>
                ))}
              </Stack>
            )}
          </>
        )}
        <Button component={RouterLink} to="/performance" variant="outlined">View all results</Button>
      </Stack>
    </Box>
  );
}
