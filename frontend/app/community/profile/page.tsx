import { Card, CardContent, Stack, Typography } from "@mui/material";
import React, { useEffect, useState } from "react";

import { getCommunityProfile, getCommunityReputation } from "../../../src/services/communityService";

export default function CommunityProfilePage() {
  const [profile, setProfile] = useState<Record<string, unknown> | null>(null);
  const [reputation, setReputation] = useState<Record<string, unknown> | null>(null);
  const username = typeof profile?.username === "string" ? profile.username : "SharpShooter23";
  const bio = typeof profile?.bio === "string" ? profile.bio : "NBA value bettor";
  const verified = typeof profile?.verified === "boolean" ? profile.verified : false;
  const score = typeof reputation?.score === "number" ? reputation.score : 94;

  useEffect(() => {
    async function load() {
      const [profileData, reputationData] = await Promise.all([getCommunityProfile(), getCommunityReputation()]);
      setProfile(profileData);
      setReputation(reputationData);
    }

    void load();
  }, []);

  return (
    <Stack spacing={2}>
      <Typography variant="h4">Community Profile</Typography>
      <Card>
        <CardContent>
          <Typography variant="h6">{username}</Typography>
          <Typography color="text.secondary">{bio} • {verified ? "Verified" : "Community member"}</Typography>
        </CardContent>
      </Card>
      <Card>
        <CardContent>
          <Typography variant="h6">Reputation</Typography>
          <Typography color="text.secondary">Score: {score}/100</Typography>
        </CardContent>
      </Card>
    </Stack>
  );
}
