import BookmarkAddOutlinedIcon from "@mui/icons-material/BookmarkAddOutlined";
import BookmarkAddedOutlinedIcon from "@mui/icons-material/BookmarkAddedOutlined";
import { Alert, Button, Stack } from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { getSavedPicks, savePrediction } from "../services/productApi";

interface SavePickButtonProps {
  predictionId: number;
}

export function SavePickButton({ predictionId }: SavePickButtonProps) {
  const queryClient = useQueryClient();
  const [savedAfterMutation, setSavedAfterMutation] = useState(false);
  const savedPicks = useQuery({
    queryKey: ["product", "saved-picks"],
    queryFn: getSavedPicks,
  });
  const saved =
    savedAfterMutation ||
    Boolean(
      savedPicks.data?.picks.some(
        (pick) => pick.prediction_id === predictionId,
      ),
    );
  const mutation = useMutation({
    mutationFn: () => savePrediction(predictionId),
    onSuccess: async () => {
      setSavedAfterMutation(true);
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
        {saved ? "Saved" : mutation.isPending ? "Saving..." : "Save Pick"}
      </Button>
      {mutation.isError ? <Alert severity="error">Unable to save pick.</Alert> : null}
    </Stack>
  );
}
