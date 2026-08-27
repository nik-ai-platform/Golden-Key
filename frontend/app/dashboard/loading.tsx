import { Grid2 as Grid, Skeleton, Stack } from "@mui/material";

export default function Loading() {
  return (
    <Stack spacing={3}>
      <Skeleton variant="rounded" height={192} />
      <Grid container spacing={2}>{Array.from({ length: 4 }, (_, index) => <Grid key={index} size={{ xs: 12, sm: 6, lg: 3 }}><Skeleton variant="rounded" height={96} /></Grid>)}</Grid>
      <Grid container spacing={2.5}>{Array.from({ length: 4 }, (_, index) => <Grid key={index} size={{ xs: 12, lg: 6 }}><Skeleton variant="rounded" height={384} /></Grid>)}</Grid>
    </Stack>
  );
}
