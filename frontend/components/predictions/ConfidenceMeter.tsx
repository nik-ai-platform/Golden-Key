import React from "react";

export function ConfidenceMeter({ value = 82 }: { value?: number }) {
  return <div>Confidence {value}%</div>;
}
