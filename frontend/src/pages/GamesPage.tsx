import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, Chip, Stack, Typography } from "@mui/material";
import { DataGrid, GridColDef } from "@mui/x-data-grid";
import { useMemo } from "react";

import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { getGames } from "../services/gamesService";
import type { Game } from "../types/games";
import { classifyError } from "../utils/apiError";

const columns: GridColDef[] = [
  { field: "id", headerName: "ID", width: 90 },
  { field: "sport", headerName: "Sport", flex: 1, minWidth: 130 },
  { field: "league", headerName: "League", flex: 1, minWidth: 130 },
  { field: "home_team_id", headerName: "Home Team", width: 130 },
  { field: "away_team_id", headerName: "Away Team", width: 130 },
  {
    field: "game_date",
    headerName: "Game Date",
    flex: 1,
    minWidth: 190,
    renderCell: (params) => <Chip size="small" color="primary" variant="outlined" label={String(params.value)} />,
  },
];

function bucketGames(games: Game[]) {
  const now = new Date();
  const upcoming: Game[] = [];
  const live: Game[] = [];
  const completed: Game[] = [];

  for (const game of games) {
    const date = new Date(game.game_date);
    const hasFinal = game.winner_team_id !== null || (game.home_score !== null && game.away_score !== null);

    if (hasFinal) {
      completed.push(game);
      continue;
    }

    if (date > now) {
      upcoming.push(game);
      continue;
    }

    live.push(game);
  }

  return { upcoming, live, completed };
}

function GamesSection({ title, rows }: { title: string; rows: Game[] }) {
  return (
    <Card>
      <CardContent>
        <Stack spacing={1}>
          <Typography variant="h6">{title}</Typography>
          {rows.length === 0 ? (
            <EmptyState description={`No ${title.toLowerCase()} at the moment.`} />
          ) : (
            <DataGrid
              rows={rows}
              columns={columns}
              autoHeight
              disableRowSelectionOnClick
              pageSizeOptions={[5, 10, 20]}
              initialState={{ pagination: { paginationModel: { pageSize: 5, page: 0 } } }}
              sx={{ backgroundColor: "white", borderRadius: 2 }}
            />
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}

export function GamesPage() {
  const gamesQuery = useQuery({ queryKey: ["games"], queryFn: getGames });
  const buckets = useMemo(() => bucketGames(gamesQuery.data ?? []), [gamesQuery.data]);

  return (
    <Stack spacing={2.5}>
      <Typography variant="h4">Games</Typography>

      {gamesQuery.isLoading && <LoadingState message="Loading games..." />}
      {gamesQuery.isError && (
        <ErrorState
          {...classifyError(gamesQuery.error)}
          onRetry={() => gamesQuery.refetch()}
        />
      )}
      {gamesQuery.isSuccess && gamesQuery.data.length === 0 && (
        <EmptyState description="No games available." />
      )}
      {gamesQuery.isSuccess && gamesQuery.data.length > 0 && (
        <Stack spacing={2}>
          <GamesSection title="Upcoming Games" rows={buckets.upcoming} />
          <GamesSection title="Live Games" rows={buckets.live} />
          <GamesSection title="Completed Games" rows={buckets.completed} />
        </Stack>
      )}
    </Stack>
  );
}
