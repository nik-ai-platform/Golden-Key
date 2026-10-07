import { Alert, Button, Card, CardContent, Stack, Typography } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";
import { PlansSummary } from "../components/PlansSummary";

export function LandingPage() {
  return <Stack spacing={4}>
    <Typography component="h1" variant="h3" className="gk-editorial">A clearer view of the game.</Typography>
    <Typography color="text.secondary">Bear A Hand Sports organizes sports model intelligence so you can understand the numbers, compare signals and make your own decisions. Predictions are uncertain—not promises of profit.</Typography>
    <Stack direction="row" spacing={2} useFlexGap flexWrap="wrap">
      <Button component={RouterLink} to="/register" variant="contained">Join Free Preview</Button>
      <Button component={RouterLink} to="/dashboard">Open dashboard</Button>
      <Button component={RouterLink} to="/how-it-works">How It Works</Button>
    </Stack>
    <Card variant="outlined"><CardContent>
      <Typography component="h2" variant="h5">Free Preview</Typography>
      <Typography>Registered accounts can view the slate overview, learn about metrics, and manage their profile, subscription and billing. Selections, odds and game analysis are not part of Free Preview.</Typography>
    </CardContent></Card>
    <Card variant="outlined"><CardContent>
      <Typography component="h2" variant="h5">Premium</Typography>
      <Typography>Active Premium unlocks full picks, odds, game analysis, saved picks, parlays and performance. Access is confirmed by the server—not a checkout redirect.</Typography>
      <PlansSummary />
    </CardContent></Card>
    <Alert severity="info">Launch billing is in sandbox validation. Do not interpret this preview as confirmation of live payment availability.</Alert>
    <Typography>For adults of legal age in their jurisdiction. We provide information, not a sportsbook or a guarantee of outcomes.</Typography>
  </Stack>;
}
