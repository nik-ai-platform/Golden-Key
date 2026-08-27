import React from "react";
import { Card, CardContent, Grid2 as Grid, Stack, Typography } from "@mui/material";

import AIAnalysisPanel from "../../components/AIAnalysisPanel";
import NPIIndicator from "../../components/NPIIndicator";
import PredictionCard from "../../components/PredictionCard";
import SimulationChart from "../../components/SimulationChart";

export default function GamesPage() {
  return (
    <Stack spacing={2.5}>
      <Stack spacing={0.5}>
        <Typography variant="h4">Games Intelligence</Typography>
        <Typography color="text.secondary">Today's games, lines, NPI scores, predictions, and AI analysis.</Typography>
      </Stack>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, lg: 7 }}>
          <PredictionCard
            matchup="Celtics vs Bulls"
            market="ATS"
            pick="Celtics ATS"
            confidence={79}
            npi={84}
            simulationProbability={61}
            risk="Medium"
            aiExplanation="Celtics maintain defensive edge and pace control despite market inflation."
          />
        </Grid>
        <Grid size={{ xs: 12, lg: 5 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 1.5 }}>Today's Games</Typography>
              <Stack spacing={1.5}>
                <NPIIndicator score={84} label="Celtics vs Bulls" />
                <NPIIndicator score={82} label="Lakers vs Suns" />
                <NPIIndicator score={87} label="Chiefs vs Bills" />
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, lg: 6 }}>
          <SimulationChart
            teamA="Team A"
            teamB="Team B"
            teamAWinProbability={63}
            projectedScore="112-105"
            variance="Moderate"
          />
        </Grid>
        <Grid size={{ xs: 12, lg: 6 }}>
          <AIAnalysisPanel
            title="AI Analysis"
            reasons={[
              "Line value remains positive versus model fair number.",
              "Matchup profile favors half-court defensive units.",
              "Scenario outcomes show stable cover probability.",
            ]}
            mainRisk="Late lineup shift before tipoff"
          />
        </Grid>
      </Grid>
    </Stack>
  );
}
