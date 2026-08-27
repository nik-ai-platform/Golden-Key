import { Card, CardContent, Stack, Typography } from "@mui/material";
import React, { useEffect, useState } from "react";

import { getCommunityLeaderboard } from "../../../src/services/communityService";

export default function CommunityLeaderboardPage() {
  const [leaderboard, setLeaderboard] = useState<Record<string, unknown>[] | null>(null);

  useEffect(() => {
    async function load() {
      const data = await getCommunityLeaderboard();
      const normalizedLeaderboard = Array.isArray(data) ? (data as Record<string, unknown>[]) : [data as Record<string, unknown>];
      setLeaderboard(normalizedLeaderboard);
    }

    void load();
  }, []);

  return (
    <Stack spacing={2}>
      <Typography variant="h4">Community Leaderboard</Typography>
      <Card>
        <CardContent>
          <Typography>Overall • ROI • Accuracy • Consistency</Typography>
        </CardContent>
      </Card>
      {(leaderboard ?? []).map((entry, index) => (
        <Card key={String(index)}>
          <CardContent>
            <Typography variant="h6">User {String(entry.user_id ?? index + 1)}</Typography>
            <Typography color="text.secondary">Score: {String(entry.score ?? "—")}</Typography>
          </CardContent>
        </Card>
      ))}
    </Stack>
  );
}
