export type PredictionMetric = "npi" | "confidence" | "projectedEdge" | "modelProbability";

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
    short: "Golden Key's 0–200 model-support score. Higher values indicate stronger calculated support within the same market.",
    detailed: "NPI summarizes Golden Key's support for a selection on a 200-point scale. Spread NPI uses weighted matchup and market factors, while moneyline and total NPI are derived from their calculated market edge. Compare NPI most carefully within the same market and model version.",
    disclaimer: "NPI supports decision-making and does not guarantee an outcome.",
  },
  confidence: {
    title: "Confidence Rating",
    ariaLabel: "Learn about Confidence Rating",
    short: "A 0–95 composite rating combining NPI, edge magnitude, and Model Probability. It is not win probability.",
    detailed: "Confidence measures combined model conviction using NPI, the magnitude of Projected Edge, and Model Probability. Golden Key caps the rating at 95. The separately displayed Model Probability is the outcome-likelihood estimate.",
    disclaimer: "Confidence describes model conviction, not certainty of winning.",
  },
  projectedEdge: {
    title: "Projected Edge",
    ariaLabel: "Learn about Projected Edge",
    short: "The difference between Golden Key's estimate and the relevant market benchmark.",
    detailed: "Projected Edge measures how far Golden Key's model differs from the benchmark used for that market.",
    disclaimer: "Projected Edge can change with market prices and does not guarantee value or profit.",
  },
  modelProbability: {
    title: "Model Probability",
    ariaLabel: "Learn about Model Probability",
    short: "Golden Key's estimated likelihood for the modeled market outcome. It is distinct from Confidence.",
    detailed: "For spreads, Model Probability comes from Golden Key's margin simulations. For moneylines, it is derived from the spread through the model's probability calculation. For totals, it is produced from the projected-total difference.",
    disclaimer: "Model Probability is an estimate, not a guaranteed outcome.",
  },
};

export function projectedEdgeMarketNote(market?: string): string | null {
  switch (market?.toLowerCase()) {
    case "spread":
      return "For spreads, edge is measured in percentage points relative to the model's 50% neutral benchmark.";
    case "moneyline":
      return "For moneylines, edge is measured in percentage points between Golden Key's model probability and the selected side's vig-removed implied market probability.";
    case "total":
      return "For totals, edge is measured in scoring points between Golden Key's projected total and the sportsbook's posted total.";
    default:
      return null;
  }
}

export function npiMarketNote(market?: string): string {
  switch (market?.toLowerCase()) {
    case "spread":
      return "This score summarizes weighted model and market support for the spread selection.";
    case "moneyline":
      return "This score reflects Golden Key's calculated support based on its moneyline probability edge.";
    case "total":
      return "This score reflects Golden Key's support based on the magnitude of the projected-total difference.";
    default:
      return predictionMetricEducation.npi.detailed;
  }
}

export function modelProbabilityMarketNote(market?: string): string | null {
  switch (market?.toLowerCase()) {
    case "spread":
      return "This spread probability is derived from Golden Key's margin simulations.";
    case "moneyline":
      return "This moneyline probability is derived from Golden Key's spread-based probability model.";
    case "total":
      return "This total probability is derived from the projected-total difference.";
    default:
      return null;
  }
}
