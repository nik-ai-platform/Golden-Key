import { useQuery } from "@tanstack/react-query";
import { Button, Card, CardContent, MenuItem, Stack, TextField, Typography } from "@mui/material";
import { DataGrid, GridColDef } from "@mui/x-data-grid";
import { useMemo, useState } from "react";

import { clearPredictionHistory, exportPredictionHistory, listPredictionHistory } from "../services/predictionHistoryService";

import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { listPredictions } from "../services/predictionsService";
import { classifyError } from "../utils/apiError";
import { formatPercent } from "../utils/format";

type PredictionSortBy = "confidence_score" | "npi_score" | "game_date" | "market" | "model_version" | "selection";
type PredictionSortOrder = "asc" | "desc";

type PredictionFilterState = {
  winnerFilter: string;
  minConfidence: string;
  sortBy: PredictionSortBy;
  sortOrder: PredictionSortOrder;
};

export function PredictionsPage() {
  const [winnerFilter, setWinnerFilter] = useState("");
  const [minConfidence, setMinConfidence] = useState("");
  const [sortBy, setSortBy] = useState<PredictionSortBy>("confidence_score");
  const [sortOrder, setSortOrder] = useState<PredictionSortOrder>("desc");
  const [submitted, setSubmitted] = useState<PredictionFilterState>({
    winnerFilter: "",
    minConfidence: "",
    sortBy: "confidence_score",
    sortOrder: "desc",
  });

  const predictionQuery = useQuery({
    queryKey: ["predictions", submitted],
    queryFn: () => listPredictions({
      winner: submitted.winnerFilter || undefined,
      minConfidence: submitted.minConfidence ? Number(submitted.minConfidence) : undefined,
      sortBy: submitted.sortBy,
      sortOrder: submitted.sortOrder,
      limit: 60,
    }),
  });

  const historyQuery = useQuery({
    queryKey: ["prediction-history"],
    queryFn: () => listPredictionHistory(),
  });

  const columns = useMemo<GridColDef[]>(
    () => [
      { field: "home_team", headerName: "Home Team", flex: 1.2, minWidth: 160 },
      { field: "away_team", headerName: "Away Team", flex: 1.2, minWidth: 160 },
      { field: "market", headerName: "Market", width: 120 },
      { field: "display_selection", headerName: "Golden Key Pick", flex: 1, minWidth: 170 },
      {
        field: "confidence_score",
        headerName: "Confidence",
        width: 130,
        valueFormatter: (value) => formatPercent(Number(value)),
      },
      {
        field: "npi_score",
        headerName: "Nik Power Index",
        width: 150,
      },
      {
        field: "model_version",
        headerName: "Model Version",
        width: 150,
      },
    ],
    [],
  );

  const rows = useMemo(
    () => (predictionQuery.data ?? []).map((row) => ({ id: row.prediction_id, ...row })),
    [predictionQuery.data],
  );

  function applyFilters() {
    setSubmitted({ winnerFilter, minConfidence, sortBy, sortOrder });
  }

  async function handleExport() {
    await exportPredictionHistory();
  }

  async function handleClear() {
    await clearPredictionHistory();
    await historyQuery.refetch();
  }

  return (
    <Stack spacing={2.5}>
      <Typography variant="h4">Predictions</Typography>
      <Card>
        <CardContent>
          <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
            <TextField
              label="Selection Filter"
              value={winnerFilter}
              onChange={(event) => setWinnerFilter(event.target.value)}
              sx={{ maxWidth: 220 }}
            />
            <TextField
              label="Min Confidence"
              value={minConfidence}
              onChange={(event) => setMinConfidence(event.target.value)}
              sx={{ maxWidth: 180 }}
            />
            <TextField
              select
              label="Sort By"
              value={sortBy}
              onChange={(event) => setSortBy(event.target.value as typeof sortBy)}
              sx={{ minWidth: 170 }}
            >
              <MenuItem value="confidence_score">Confidence</MenuItem>
              <MenuItem value="npi_score">Nik Power Index</MenuItem>
              <MenuItem value="game_date">Game Date</MenuItem>
              <MenuItem value="market">Market</MenuItem>
              <MenuItem value="model_version">Model Version</MenuItem>
              <MenuItem value="selection">Selection</MenuItem>
            </TextField>
            <TextField
              select
              label="Order"
              value={sortOrder}
              onChange={(event) => setSortOrder(event.target.value as typeof sortOrder)}
              sx={{ minWidth: 120 }}
            >
              <MenuItem value="desc">Desc</MenuItem>
              <MenuItem value="asc">Asc</MenuItem>
            </TextField>
            <Button variant="contained" onClick={applyFilters}>
              Apply
            </Button>
          </Stack>
        </CardContent>
      </Card>

      {predictionQuery.isLoading && <LoadingState message="Loading predictions..." />}
      {predictionQuery.isError && (
        <ErrorState
          {...classifyError(predictionQuery.error)}
          onRetry={() => predictionQuery.refetch()}
        />
      )}
      {predictionQuery.isSuccess && rows.length === 0 && (
        <EmptyState description="No predictions matched the selected filters." />
      )}
      {predictionQuery.isSuccess && rows.length > 0 && (
        <DataGrid
          rows={rows}
          columns={columns}
          autoHeight
          disableRowSelectionOnClick
          pageSizeOptions={[10, 25, 50]}
          initialState={{ pagination: { paginationModel: { pageSize: 10, page: 0 } } }}
          sx={{ backgroundColor: "white", borderRadius: 2 }}
        />
      )}

      <Card>
        <CardContent>
          <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} alignItems="center" justifyContent="space-between">
            <Typography variant="h6">Prediction History</Typography>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
              <Button variant="outlined" onClick={() => void handleExport()}>
                Export
              </Button>
              <Button variant="outlined" color="warning" onClick={() => void handleClear()}>
                Clear
              </Button>
            </Stack>
          </Stack>
          {historyQuery.isLoading && <LoadingState message="Loading history..." />}
          {historyQuery.isError && <Typography color="error">Unable to load history.</Typography>}
          {historyQuery.isSuccess && (
            <Stack spacing={1} mt={2}>
              {(historyQuery.data ?? []).length === 0 ? (
                <Typography color="text.secondary">No history entries yet.</Typography>
              ) : (
                (historyQuery.data ?? []).slice(0, 8).map((entry) => (
                  <Card key={entry.id} variant="outlined">
                    <CardContent>
                      <Typography variant="body2">
                        {entry.prediction ?? "Unknown"} · {entry.model_version ?? "n/a"} · {entry.result_status ?? "pending"}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Confidence: {entry.confidence ?? "n/a"} · Market: {entry.market_line ?? "n/a"}
                      </Typography>
                    </CardContent>
                  </Card>
                ))
              )}
            </Stack>
          )}
        </CardContent>
      </Card>
    </Stack>
  );
}
