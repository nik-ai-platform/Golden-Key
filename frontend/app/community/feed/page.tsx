import { Card, CardContent, Stack, Typography } from "@mui/material";
import React, { useEffect, useState } from "react";

import { getCommunityDiscussions, getCommunityFeed } from "../../../src/services/communityService";

export default function CommunityFeedPage() {
  const [feed, setFeed] = useState<Record<string, unknown> | null>(null);
  const [discussions, setDiscussions] = useState<Record<string, unknown>[] | null>(null);
  const feedEntry = Array.isArray(feed?.feed) ? feed.feed[0] : "Celtics -4.5";
  const consensus = typeof feed?.consensus === "number" ? feed.consensus : 0.76;

  useEffect(() => {
    async function load() {
      const [feedData, discussionsData] = await Promise.all([getCommunityFeed(), getCommunityDiscussions()]);
      setFeed(feedData);
      const normalizedDiscussions = Array.isArray(discussionsData)
        ? (discussionsData as Record<string, unknown>[])
        : [discussionsData as Record<string, unknown>];
      setDiscussions(normalizedDiscussions);
    }

    void load();
  }, []);

  return (
    <Stack spacing={2}>
      <Typography variant="h4">Community Feed</Typography>
      <Card>
        <CardContent>
          <Typography variant="h6">{String(feedEntry)}</Typography>
          <Typography color="text.secondary">Consensus: {Math.round(consensus * 100)}%</Typography>
        </CardContent>
      </Card>
      {(discussions ?? []).map((discussion, index) => (
        <Card key={String(index)}>
          <CardContent>
            <Typography variant="h6">{String(discussion.body ?? "Discussion")}</Typography>
            <Typography color="text.secondary">Likes: {String(discussion.likes ?? 0)}</Typography>
          </CardContent>
        </Card>
      ))}
    </Stack>
  );
}
