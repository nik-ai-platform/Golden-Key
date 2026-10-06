export type PredictionMetric = "npi" | "confidence" | "modelProbability" | "projectedEdge" | "risk";

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
    short: "Nik Power Index is a market-specific model score, not probability. Interpret each score within its market and model configuration.",
    detailed: "NPI means Nik Power Index. It summarizes the model inputs used for that market, not the chance of winning. Spread, moneyline, and total NPI have different meanings. Scores should not be directly compared across different market types or model configurations. Higher spread NPI does not always mean stronger support for the selected pick.",
    disclaimer: "NPI supports decision-making and does not guarantee an outcome.",
  },
  confidence: {
    title: "Confidence Rating",
    ariaLabel: "Learn about Confidence Rating",
    short: "A 0–95 composite rating built from NPI, projected-edge magnitude, and the model probability input. It is not win probability.",
    detailed: "Confidence Rating is a 0–95 composite rating built from NPI, projected-edge magnitude, and the model probability input. It is not win probability and should not be read as “percent chance to win.” Historical Confidence and Risk remain the values produced by their original model version.",
    disclaimer: "Confidence describes model conviction, not certainty of winning.",
  },
  modelProbability: {
    title: "Model Probability",
    ariaLabel: "Learn about Model Probability",
    short: "The model's estimated likelihood of the displayed selection—team, OVER, or UNDER. It is distinct from Confidence Rating and is not a guarantee.",
    detailed: "Model Probability estimates the likelihood of the displayed selection—team, OVER, or UNDER—according to the model. It is not a guarantee and has not yet been presented as a fully calibrated probability. Spreads use margin simulations, moneylines use a spread-based estimate, and totals use a projected-total heuristic rather than a simulation.",
    disclaimer: "Model Probability is an estimate, not a guaranteed outcome.",
  },
  projectedEdge: {
    title: "Projected Edge",
    ariaLabel: "Learn about Projected Edge",
    short: "A model-to-benchmark difference: percentage points for spreads and moneylines, scoring points for totals. It is not a universal expected-profit figure.",
    detailed: "Projected Edge compares the model with a market-specific benchmark. Spread and moneyline edges use percentage points; total edges use scoring points. Projected edge is not a universal expected-profit figure.",
    disclaimer: "An edge estimate does not guarantee value at a changed sportsbook price.",
  },
  risk: {
    title: "Risk Level",
    ariaLabel: "Learn about Risk Level",
    short: "Derived from Confidence Rating: Low at 80 or higher, Medium at 65 through 79.99, and High below 65. It is not an independent bankroll-risk or volatility model.",
    detailed: "Risk Level is currently derived from Confidence Rating. It is not an independent bankroll-risk or volatility model, and it does not measure how much you can afford to wager.",
    disclaimer: "Users remain responsible for wagering decisions.",
  },
};

export const npiMarketEducation = [
  { market: "spread", title: "Spread NPI", description: "A weighted line, scoring-environment, and fixed-rule score. It is home-oriented in its underlying construction, while the displayed Model Probability is adjusted to the selected side." },
  { market: "moneyline", title: "Moneyline NPI", description: "A score based on the difference between the model’s win estimate and the sportsbook market’s vig-adjusted implied probability." },
  { market: "total", title: "Total NPI", description: "A score based on how far the posted game total is from the model’s sport-specific scoring baseline." },
] as const;

export const projectedEdgeEducation = [
  { market: "spread", title: "Spread", description: "Percentage-point difference from a 50% cover benchmark." },
  { market: "moneyline", title: "Moneyline", description: "Percentage-point difference from the sportsbook’s vig-free implied probability." },
  { market: "total", title: "Total", description: "Scoring-point difference between the model projection and posted total." },
] as const;

export const npiReportingNote = "Numeric NPI reporting ranges are not calibrated strength levels. Scores from different markets or model configurations should not be directly compared.";
export const npiBandsExplanation = "Bear A Hand Sports does not currently publish named NPI strength bands. Earlier numeric ranges are reporting buckets, not proven levels such as Weak, Strong, or Elite. Strength bands will only be introduced after sufficient settled predictions support stable sport-, market-, and model-specific comparisons.";
export const npiBandsNotice = "Strength bands are under evaluation as Bear A Hand Sports collects settled predictions across each sport and market.";
export const riskThresholds = [
  { title: "Low", description: "Confidence Rating 80 or higher." },
  { title: "Medium", description: "Confidence Rating 65 through 79.99." },
  { title: "High", description: "Confidence Rating below 65." },
] as const;
export const dashboardSequence = [
  "Read the current game and market snapshot.",
  "Calculate market-specific model metrics.",
  "Exclude unavailable or incomplete recommendations.",
  "Rank eligible selections within the model.",
  "Publish the current supported prediction for each game and market.",
  "Settle completed predictions for Performance reporting.",
] as const;
export const responsibleInterpretation = [
  "Metrics are analytical estimates, not guarantees.",
  "Sports outcomes contain uncertainty.",
  "Past Performance does not guarantee future results.",
  "Compare picks within the same market context.",
  "Check current sportsbook prices because lines and odds change.",
  "Users remain responsible for wagering decisions.",
] as const;

export function npiMarketNote(market?: string): string {
  return npiMarketEducation.find((item) => item.market === market?.toLowerCase())?.description
    ?? predictionMetricEducation.npi.detailed;
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
