import React from "react";
import { Card, CardContent, Stack, Typography } from "@mui/material";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type SimulationChartProps = {
  teamA: string;
  teamB: string;
  teamAWinProbability: number;
  projectedScore: string;
  variance: string;
};

export default function SimulationChart({ teamA, teamB, teamAWinProbability, projectedScore, variance }: SimulationChartProps) {
  const teamBWinProbability = Math.max(0, 100 - teamAWinProbability);
  const data = [
    { scenario: "Low", teamA: teamAWinProbability - 8, teamB: teamBWinProbability + 8 },
    { scenario: "Base", teamA: teamAWinProbability, teamB: teamBWinProbability },
    { scenario: "High", teamA: teamAWinProbability + 6, teamB: teamBWinProbability - 6 },
  ];

  return (
    <Card>
      <CardContent>
        <Stack spacing={1.5}>
          <Typography variant="h6">Simulation Display</Typography>
          <Typography>{teamA} Win: {teamAWinProbability}%</Typography>
          <Typography>Projected Score: {projectedScore}</Typography>
          <Typography>Variance: {variance}</Typography>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="scenario" />
              <YAxis domain={[0, 100]} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="teamA" name={teamA} stroke="#0f766e" strokeWidth={2} />
              <Line type="monotone" dataKey="teamB" name={teamB} stroke="#b45309" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </Stack>
      </CardContent>
    </Card>
  );
}
