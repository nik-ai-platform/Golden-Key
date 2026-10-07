import { Alert, Button, Card, CardContent, Stack, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { Link as RouterLink } from "react-router-dom";
import { getPreview } from "../services/productPreviewService";
import { LoadingState } from "../components/LoadingState";

export function FreePreviewPage() {
  const query = useQuery({ queryKey: ["product", "preview"], queryFn: getPreview, retry: false });
  return <Stack spacing={3}>
    <Typography variant="h4" component="h1" className="gk-editorial">Free Preview dashboard</Typography>
    <Typography>Explore the upcoming slate without picks, odds or Premium analysis.</Typography>
    <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
      <Button component={RouterLink} to="/profile" variant="contained">Explore Premium</Button>
      <Button component={RouterLink} to="/how-it-works">Understand the metrics</Button>
    </Stack>
    {query.isPending ? <LoadingState message="Loading slate overview..." /> : null}
    {query.isError ? <Alert severity="error" action={<Button onClick={() => void query.refetch()}>Retry</Button>}>Unable to load the slate overview.</Alert> : null}
    {query.data ? <>
      <Typography component="h2" variant="h6">Slate overview · {query.data.count} games</Typography>
      {query.data.games.length === 0 ? <Alert severity="info">No upcoming games are available right now. Check back later.</Alert> : null}
      {query.data.games.map((game) => <Card variant="outlined" key={game.game_id}><CardContent>
        <Typography variant="overline">{game.sport} · {game.league}</Typography>
        <Typography component="h3" variant="h6" sx={{ overflowWrap: "anywhere" }}>{game.away_team} at {game.home_team}</Typography>
        <Typography color="text.secondary">{game.start_time ? new Date(game.start_time).toLocaleString() : "Start time to be confirmed"} · {game.status}</Typography>
      </CardContent></Card>)}
    </> : null}
  </Stack>;
}
