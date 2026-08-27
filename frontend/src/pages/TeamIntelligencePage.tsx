import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, Grid2 as Grid, MenuItem, Stack, TextField, Typography } from "@mui/material";
import { useMemo, useState } from "react";

import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { getTeamIntelligenceDetail, getTeams } from "../services/teamService";
import { classifyError } from "../utils/apiError";
import { formatPercent } from "../utils/format";

export function TeamIntelligencePage() {
  const [selectedId, setSelectedId] = useState<number>(1);
  const teamsQuery = useQuery({ queryKey: ["teams"], queryFn: getTeams });

  const teamOptions = useMemo(() => teamsQuery.data ?? [], [teamsQuery.data]);

  const intelligenceQuery = useQuery({
    queryKey: ["team-intelligence", selectedId],
    queryFn: () => getTeamIntelligenceDetail(selectedId),
    enabled: Number.isFinite(selectedId) && selectedId > 0,
  });

  const combinedError = teamsQuery.error ?? intelligenceQuery.error;

  return (
    <Stack spacing={2.5}>
      <Typography variant="h4">Team Intelligence</Typography>

      <TextField
        select
        label="Team"
        value={selectedId}
        onChange={(event) => setSelectedId(Number(event.target.value))}
        sx={{ maxWidth: 360 }}
      >
        {teamOptions.map((team) => (
          <MenuItem key={team.id} value={team.id}>{team.name} ({team.league})</MenuItem>
        ))}
      </TextField>

      {(teamsQuery.isLoading || intelligenceQuery.isLoading) && <LoadingState message="Loading team intelligence..." />}
      {(teamsQuery.isError || intelligenceQuery.isError) && (
        <ErrorState
          {...classifyError(combinedError)}
          onRetry={() => {
            void teamsQuery.refetch();
            void intelligenceQuery.refetch();
          }}
        />
      )}

      {intelligenceQuery.isSuccess && !intelligenceQuery.data && (
        <EmptyState />
      )}

      {intelligenceQuery.data && (
        <Grid container spacing={2}>
          {[
            ["Momentum", formatPercent(intelligenceQuery.data.momentum)],
            ["Trend", intelligenceQuery.data.trend.toUpperCase()],
            ["Strength", String(intelligenceQuery.data.strength_rating)],
            ["Offense", String(intelligenceQuery.data.offensive_rating)],
            ["Defense", String(intelligenceQuery.data.defensive_rating)],
            ["Home Record", intelligenceQuery.data.home_record ?? "N/A"],
            ["Away Record", intelligenceQuery.data.away_record ?? "N/A"],
          ].map(([label, value]) => (
            <Grid size={{ xs: 12, sm: 6, md: 4 }} key={label}>
              <Card sx={{ height: "100%" }}>
                <CardContent>
                  <Typography variant="overline" color="text.secondary">{label}</Typography>
                  <Typography variant="h6">{value}</Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}
    </Stack>
  );
}
