import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, Grid2 as Grid, Stack, Typography } from "@mui/material";
import {
  Bar,
  BarChart,
  Legend,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { getAccuracy, getBacktesting, getCalibration, getConfidence, getDailyTrends } from "../services/analyticsService";
import { classifyError } from "../utils/apiError";
import { formatPercent } from "../utils/format";

export function AnalyticsPage() {
  const accuracyQuery = useQuery({ queryKey: ["accuracy"], queryFn: getAccuracy });
  const confidenceQuery = useQuery({ queryKey: ["confidence"], queryFn: getConfidence });
  const calibrationQuery = useQuery({ queryKey: ["calibration"], queryFn: getCalibration });
  const trendsQuery = useQuery({ queryKey: ["daily-trends"], queryFn: getDailyTrends });
  const backtestQuery = useQuery({ queryKey: ["backtesting"], queryFn: getBacktesting });

  const hasError = accuracyQuery.isError || confidenceQuery.isError || calibrationQuery.isError || trendsQuery.isError || backtestQuery.isError;
  const anyError = accuracyQuery.error ?? confidenceQuery.error ?? calibrationQuery.error ?? trendsQuery.error ?? backtestQuery.error;

  const modelRows = accuracyQuery.data ? Object.entries(accuracyQuery.data.model_accuracy).map(([model, value]) => ({ model, accuracy: value.accuracy })) : [];
  const confidenceRows = confidenceQuery.data?.buckets ?? [];
  const calibrationRows = calibrationQuery.data?.buckets ?? [];

  return (
    <Stack spacing={2.5}>
      <Typography variant="h4">Analytics</Typography>
      {(accuracyQuery.isLoading || confidenceQuery.isLoading || calibrationQuery.isLoading || trendsQuery.isLoading || backtestQuery.isLoading) && <LoadingState message="Loading analytics..." />}
      {hasError && (
        <ErrorState
          {...classifyError(anyError)}
          onRetry={() => {
            void accuracyQuery.refetch();
            void confidenceQuery.refetch();
            void calibrationQuery.refetch();
            void trendsQuery.refetch();
            void backtestQuery.refetch();
          }}
        />
      )}

      {accuracyQuery.isSuccess && confidenceQuery.isSuccess && calibrationQuery.isSuccess && trendsQuery.isSuccess && backtestQuery.isSuccess && (
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <StatCard label="Historical Accuracy" value={formatPercent(accuracyQuery.data.overall_accuracy)} />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <StatCard label="Backtest Snapshots" value={String(backtestQuery.data.snapshots_processed)} />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <StatCard label="Backtest Evaluations" value={String(backtestQuery.data.evaluations_created)} />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <StatCard label="Model Count" value={String(backtestQuery.data.model_versions.length)} />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <StatCard label="Calibration Reliability" value={formatPercent(calibrationQuery.data.overall_reliability)} />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <StatCard label="Calibration Error (MAE)" value={formatPercent(calibrationQuery.data.overall_error)} />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <StatCard label="Max Bucket Error" value={formatPercent(calibrationQuery.data.maximum_error)} />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <StatCard label="Calibrated Samples" value={String(calibrationQuery.data.total_predictions)} />
          </Grid>
        </Grid>
      )}

      {calibrationQuery.isSuccess && calibrationRows.length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>Calibration by Confidence Bucket</Typography>
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={calibrationRows}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="range" />
                <YAxis />
                <Tooltip formatter={(value: number) => `${value.toFixed(2)}%`} />
                <Legend />
                <Bar dataKey="confidence" name="Predicted Confidence" fill="#0369a1" radius={[6, 6, 0, 0]} />
                <Bar dataKey="accuracy" name="Observed Accuracy" fill="#16a34a" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {confidenceQuery.isSuccess && confidenceRows.length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>Confidence Buckets</Typography>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={confidenceRows}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="label" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="accuracy" fill="#ca8a04" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {accuracyQuery.isSuccess && modelRows.length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>Model Comparison</Typography>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={modelRows}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="model" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="accuracy" fill="#0f766e" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {trendsQuery.isSuccess && trendsQuery.data.length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>Daily Trend Accuracy</Typography>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={trendsQuery.data}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="period" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="accuracy" stroke="#0f766e" strokeWidth={3} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {trendsQuery.isSuccess && trendsQuery.data.length === 0 && (
        <EmptyState description="Trend data is not available yet." />
      )}
    </Stack>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardContent>
        <Typography variant="overline" color="text.secondary">{label}</Typography>
        <Typography variant="h5" color="primary">{value}</Typography>
      </CardContent>
    </Card>
  );
}
