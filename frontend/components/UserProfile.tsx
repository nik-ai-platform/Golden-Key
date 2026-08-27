"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, Typography } from "@mui/material";

import { getToken } from "../services/session";

type UserProfileResponse = {
  id: number;
  email: string;
  username: string;
  premium: boolean;
};

export default function UserProfile() {
  const [user, setUser] = useState<UserProfileResponse | null>(null);

  useEffect(() => {
    fetch("http://localhost:8000/api/v1/users/me", {
      headers: {
        Authorization: `Bearer ${getToken()}`,
      },
    })
      .then((res) => res.json())
      .then((data) => setUser(data));
  }, []);

  if (!user) {
    return null;
  }

  return (
    <Card>
      <CardContent>
        <Typography variant="h6">Welcome {user.username}</Typography>
        <Typography color="text.secondary">Premium: {user.premium ? "Yes" : "No"}</Typography>
      </CardContent>
    </Card>
  );
}