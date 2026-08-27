"use client";

import { useState } from "react";
import { Alert, Button, Stack } from "@mui/material";

import { savePrediction } from "../services/api";

export default function SavePickButton({ predictionId }: { predictionId: number }) {
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function save() {
    setLoading(true);
    setError("");
    try {
      await savePrediction(predictionId);
      setSaved(true);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to save pick");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Stack spacing={1} alignItems="flex-start">
      <Button variant="outlined" onClick={save} disabled={saved || loading}>
        {saved ? "Saved" : loading ? "Saving..." : "Save Pick"}
      </Button>
      {error ? <Alert severity="error">{error}</Alert> : null}
    </Stack>
  );
}