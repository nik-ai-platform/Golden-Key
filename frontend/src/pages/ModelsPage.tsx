import { useEffect, useMemo, useState } from "react";

import { useQuery } from "@tanstack/react-query";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  FormControl,
  Grid2 as Grid,
  InputLabel,
  MenuItem,
  Select,
  Skeleton,
  Stack,
  Typography,
} from "@mui/material";
import { Bar, BarChart, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { getModelLearning } from "../services/analyticsService";
import { compareModels, getModels } from "../services/modelEvaluationService";
import { classifyError } from "../utils/apiError";
import { formatNumber, formatPercent } from "../utils/format";

export function ModelsPage() {
  const modelsQuery = useQuery({ queryKey: ["models"], queryFn: getModels });
  const learningQuery = useQuery({ queryKey: ["model-learning"], queryFn: getModelLearning });
  const [currentVersion, setCurrentVersion] = useState("");
  const [candidateVersion, setCandidateVersion] = useState("");

  const versions = useMemo(
    () => (modelsQuery.data ?? []).map((entry) => entry.model_version),
    [modelsQuery.data],
  );

  useEffect(() => {
    if (!versions.length) {
      return;
    }

    if (!currentVersion) {
      setCurrentVersion(versions[0]);
    }

    if (!candidateVersion) {
      setCandidateVersion(versions[1] ?? versions[0]);
    }
  }, [versions, currentVersion, candidateVersion]);

  const comparisonQuery = useQuery({
    queryKey: ["model-compare", currentVersion, candidateVersion],
    queryFn: () => compareModels({ current_version: currentVersion, candidate_version: candidateVersion }),
    enabled: Boolean(currentVersion && candidateVersion),
  });

  const hasError = modelsQuery.isError || comparisonQuery.isError || learningQuery.isError;
  const anyError = modelsQuery.error ?? comparisonQuery.error ?? learningQuery.error;

  const deltaRows = comparisonQuery.data
    ? [
        {
          metric: "Accuracy Delta",
          value: comparisonQuery.data.candidate_model.accuracy - comparisonQuery.data.current_model.accuracy,
        },
        {
          metric: "Calibration Improvement",
          value: comparisonQuery.data.current_model.calibration - comparisonQuery.data.candidate_model.calibration,
        },
        {
          metric: "Confidence Delta",
          value: comparisonQuery.data.candidate_model.average_confidence - comparisonQuery.data.current_model.average_confidence,
        },
      ]
    : [];

  return (
    <Stack spacing={2.5}>
      <Typography variant="h4">Models</Typography>

      {modelsQuery.isLoading && <LoadingState message="Loading model registry..." />}

      {hasError && (
        <ErrorState
          {...classifyError(anyError)}
          onRetry={() => {
            void modelsQuery.refetch();
            void comparisonQuery.refetch();
            void learningQuery.refetch();
          }}
        />
      )}

      {learningQuery.isLoading && (
        <Card data-testid="model-learning-skeleton">
          <CardContent>
            <Typography variant="h6" gutterBottom>Model Learning</Typography>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Skeleton variant="text" width="65%" />
                <Skeleton variant="text" width="85%" height={34} />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Skeleton variant="text" width="70%" />
                <Skeleton variant="text" width="75%" height={34} />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Skeleton variant="text" width="72%" />
                <Skeleton variant="text" width="50%" height={34} />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Skeleton variant="text" width="68%" />
                <Skeleton variant="text" width="80%" height={34} />
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}

      {learningQuery.isSuccess && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>Model Learning</Typography>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <LearningStat label="Current Model" value={learningQuery.data.current_model} />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <LearningStat label="Training Samples" value={formatNumber(learningQuery.data.training_samples)} />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <LearningStat label="Candidate Models" value={formatNumber(learningQuery.data.candidate_models)} />
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <LearningStat label="Best Candidate" value={learningQuery.data.best_candidate ?? "None"} />
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}

      {modelsQuery.isSuccess && modelsQuery.data.length === 0 && (
        <Alert severity="info">No models are available in the registry yet.</Alert>
      )}

      {modelsQuery.isSuccess && modelsQuery.data.length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>Model Comparison</Typography>
            <Grid container spacing={2} alignItems="center">
              <Grid size={{ xs: 12, md: 4 }}>
                <FormControl fullWidth>
                  <InputLabel id="current-model-label">Current Model</InputLabel>
                  <Select
                    labelId="current-model-label"
                    label="Current Model"
                    value={currentVersion}
                    onChange={(event) => setCurrentVersion(event.target.value)}
                  >
                    {versions.map((version) => (
                      <MenuItem key={version} value={version}>{version}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid size={{ xs: 12, md: 4 }}>
                <FormControl fullWidth>
                  <InputLabel id="candidate-model-label">Candidate Model</InputLabel>
                  <Select
                    labelId="candidate-model-label"
                    label="Candidate Model"
                    value={candidateVersion}
                    onChange={(event) => setCandidateVersion(event.target.value)}
                  >
                    {versions.map((version) => (
                      <MenuItem key={version} value={version}>{version}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid size={{ xs: 12, md: 4 }}>
                <Button variant="outlined" onClick={() => void comparisonQuery.refetch()} disabled={!currentVersion || !candidateVersion}>
                  Run Comparison
                </Button>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}

      {comparisonQuery.isLoading && <LoadingState message="Running model comparison..." />}

      {comparisonQuery.isSuccess && (
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, md: 6 }}>
            <MetricCard
              title={`Current: ${currentVersion}`}
              accuracy={comparisonQuery.data.current_model.accuracy}
              calibration={comparisonQuery.data.current_model.calibration}
              averageConfidence={comparisonQuery.data.current_model.average_confidence}
              predictions={comparisonQuery.data.current_model.predictions}
            />
          </Grid>
          <Grid size={{ xs: 12, md: 6 }}>
            <MetricCard
              title={`Candidate: ${candidateVersion}`}
              accuracy={comparisonQuery.data.candidate_model.accuracy}
              calibration={comparisonQuery.data.candidate_model.calibration}
              averageConfidence={comparisonQuery.data.candidate_model.average_confidence}
              predictions={comparisonQuery.data.candidate_model.predictions}
            />
          </Grid>
          <Grid size={{ xs: 12 }}>
            <Card>
              <CardContent>
                <Typography variant="h6">Recommendation</Typography>
                <Typography variant="h5" color={comparisonQuery.data.winner === "candidate" ? "success.main" : "primary.main"}>
                  {comparisonQuery.data.winner === "candidate" ? "Promote Candidate" : "Keep Current"}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid size={{ xs: 12 }}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Performance Delta</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  Positive values favor the candidate model.
                </Typography>
                <Box sx={{ width: "100%", height: 260 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={deltaRows} layout="vertical" margin={{ top: 12, right: 24, left: 24, bottom: 12 }}>
                      <XAxis type="number" />
                      <YAxis type="category" dataKey="metric" width={150} />
                      <Tooltip formatter={(value: number) => `${value.toFixed(2)}%`} />
                      <Bar dataKey="value" radius={[6, 6, 6, 6]}>
                        {deltaRows.map((row) => (
                          <Cell key={row.metric} fill={row.value >= 0 ? "#15803d" : "#b91c1c"} />
                        ))}
                        <LabelList dataKey="value" position="right" formatter={(value: number) => `${value.toFixed(2)}%`} />
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}
    </Stack>
  );
}

function LearningStat({ label, value }: { label: string; value: string }) {
  return (
    <Stack spacing={0.25}>
      <Typography variant="overline" color="text.secondary">{label}</Typography>
      <Typography variant="h6">{value}</Typography>
    </Stack>
  );
}

function MetricCard({
  title,
  accuracy,
  calibration,
  averageConfidence,
  predictions,
}: {
  title: string;
  accuracy: number;
  calibration: number;
  averageConfidence: number;
  predictions: number;
}) {
  return (
    <Card sx={{ height: "100%" }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>{title}</Typography>
        <Stack spacing={1}>
          <Typography>Accuracy: {formatPercent(accuracy)}</Typography>
          <Typography>Calibration Error: {formatPercent(calibration)}</Typography>
          <Typography>Average Confidence: {formatPercent(averageConfidence)}</Typography>
          <Typography>Predictions: {formatNumber(predictions)}</Typography>
        </Stack>
      </CardContent>
    </Card>
  );
}