export type PredictionMetric = "npi" | "confidence" | "modelProbability";

export type PredictionMetricEducation = {
  title: string;
  ariaLabel: string;
  short: string;
  detailed: string;
  disclaimer: string;
};

export const predictionMetricEducation: Record<PredictionMetric, PredictionMetricEducation> = {
  npi: {
    title: "Nik Power Index (NPI)",
    ariaLabel: "Learn about NPI",
    short: "Bear A Hand Sports' 0–200 model-support score. Higher values indicate stronger calculated support within the same market.",
    detailed: "NPI summarizes Bear A Hand Sports' support for a selection on a 200-point scale. Spread NPI uses weighted matchup and market factors, while moneyline and total NPI are derived from their calculated market edge. Compare NPI most carefully within the same market and model version.",
    disclaimer: "NPI supports decision-making and does not guarantee an outcome.",
  },
  confidence: {
    title: "Confidence Rating",
    ariaLabel: "Learn about Confidence Rating",
    short: "A 0–95 composite rating combining NPI, edge magnitude, and Model Probability. It is not win probability.",
    detailed: "Confidence Rating combines NPI, edge magnitude, and the model probability input, capped at 95. NPI-5.0 uses selected-side probability. Historical Confidence and Risk remain the values produced by their original model version; reads do not recalculate them. Confidence is not win probability.",
    disclaimer: "Confidence describes model conviction, not certainty of winning.",
  },
  modelProbability: {
    title: "Model Probability",
    ariaLabel: "Learn about Model Probability",
    short: "Bear A Hand Sports' estimated likelihood for the modeled market outcome. It is distinct from Confidence.",
    detailed: "For spreads, Model Probability comes from Bear A Hand Sports' margin simulations. For moneylines, it is derived from the spread through the model's probability calculation. For totals, it is produced from the projected-total difference.",
    disclaimer: "Model Probability is an estimate, not a guaranteed outcome.",
  },
};

export function npiMarketNote(market?: string): string {
  switch (market?.toLowerCase()) {
    case "spread":
      return "This score summarizes weighted model and market support for the spread selection.";
    case "moneyline":
      return "This score reflects Bear A Hand Sports' calculated support based on its moneyline probability edge.";
    case "total":
      return "This score reflects Bear A Hand Sports' support based on the magnitude of the projected-total difference.";
    default:
      return predictionMetricEducation.npi.detailed;
  }
}

export function modelProbabilityMarketNote(market?: string): string | null {
  switch (market?.toLowerCase()) {
    case "spread":
      return "Model Probability estimates the selected team covering the spread, using Bear A Hand Sports' margin simulations.";
    case "moneyline":
      return "Model Probability estimates the selected team winning, using Bear A Hand Sports' spread-based probability model.";
    case "total":
      return "Model Probability estimates the selected OVER/UNDER outcome according to the projected-total model heuristic, not a simulation.";
    default:
      return null;
  }
}
