import { Card, CardContent, Stack, Typography } from "@mui/material";
import React, { useEffect, useState } from "react";

import { getCommunityStrategies } from "../../../src/services/communityService";

export default function CommunityStrategiesPage() {
  const [strategies, setStrategies] = useState<Record<string, unknown>[] | null>(null);

  useEffect(() => {
    async function load() {
      const data = await getCommunityStrategies();
      const normalizedStrategies = Array.isArray(data) ? (data as Record<string, unknown>[]) : [data as Record<string, unknown>];
      setStrategies(normalizedStrategies);
    }

    void load();
  }, []);

  return (
    <Stack spacing={2}>
      <Typography variant="h4">Community Strategies</Typography>
      {(strategies ?? []).map((strategy, index) => (
        <Card key={String(index)}>
          <CardContent>
            <Typography variant="h6">{String(strategy.name ?? "Strategy")}</Typography>
            <Typography color="text.secondary">Sport: {String(strategy.sport ?? "NBA")} • Market: {String(strategy.market ?? "ATS")}</Typography>
          </CardContent>
        </Card>
      ))}
    </Stack>
  );
}
