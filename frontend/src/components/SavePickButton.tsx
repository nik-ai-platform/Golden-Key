import BookmarkAddOutlinedIcon from "@mui/icons-material/BookmarkAddOutlined";
import BookmarkAddedOutlinedIcon from "@mui/icons-material/BookmarkAddedOutlined";
import { Alert, Button, Stack } from "@mui/material";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { savePrediction } from "../services/productApi";

interface SavePickButtonProps {
  predictionId: number;
}

export function SavePickButton({ predictionId }: SavePickButtonProps) {
  const queryClient = useQueryClient();
  const [saved, setSaved] = useState(false);
  const mutation = useMutation({
    mutationFn: () => savePrediction(predictionId),
    onSuccess: async () => {
      setSaved(true);
      await queryClient.invalidateQueries({ queryKey: ["product", "saved-picks"] });
    },
  });

  return (
    <Stack spacing={1} alignItems="flex-start">
      <Button
        type="button"
        variant="outlined"
        startIcon={saved ? <BookmarkAddedOutlinedIcon /> : <BookmarkAddOutlinedIcon />}
        disabled={mutation.isPending || saved}
        onClick={() => mutation.mutate()}
      >
        {saved ? "Saved" : mutation.isPending ? "Saving..." : "Save pick"}
      </Button>
      {mutation.isError ? <Alert severity="error">Unable to save pick.</Alert> : null}
    </Stack>
  );
}
