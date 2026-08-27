import { Card, CardContent, Chip, Grid2 as Grid, Stack, Typography } from "@mui/material";
import React, { useEffect, useState } from "react";

import { getCommunityFeed, getCommunityProfile } from "../../src/services/communityService";

export default function CommunityPage() {
  const [profile, setProfile] = useState<Record<string, unknown> | null>(null);
  const [feed, setFeed] = useState<Record<string, unknown> | null>(null);
  const username = typeof profile?.username === "string" ? profile.username : "SharpShooter23";
  const bio = typeof profile?.bio === "string" ? profile.bio : "NBA value bettor";
  const verified = typeof profile?.verified === "boolean" ? profile.verified : false;
  const feedEntry = Array.isArray(feed?.feed) ? feed.feed[0] : "Celtics -4.5";
  const consensus = typeof feed?.consensus === "number" ? feed.consensus : 0.76;

  useEffect(() => {
    async function load() {
      const [profileData, feedData] = await Promise.all([getCommunityProfile(), getCommunityFeed()]);
      setProfile(profileData);
      setFeed(feedData);
    }

    void load();
  }, []);

  return (
    <Stack spacing={2}>
      <Typography variant="h4">Golden Key Community</Typography>
      <Typography color="text.secondary">Trending picks, verified voices, and crowd intelligence in one place.</Typography>
      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6">🔥 Trending</Typography>
              <Typography variant="h5">{String(feedEntry)}</Typography>
              <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                <Chip label={`Consensus ${Math.round(consensus * 100)}%`} />
                <Chip label="AI Alignment HIGH" />
              </Stack>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6">Top Analysts</Typography>
              <Typography>{verified ? "Verified member" : "Community member"}</Typography>
              <Typography color="text.secondary">{username}</Typography>
              <Typography variant="body2" color="text.secondary">{bio}</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Stack>
  );
}
