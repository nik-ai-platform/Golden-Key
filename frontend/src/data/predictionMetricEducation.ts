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
    short: "NPI is a model score for one market. It is not the chance that a pick will win.",
    detailed: "NPI (Nik Power Index) summarizes model inputs for a market. It is a score, not a chance to win. Spread, moneyline, and total scores describe different things, so do not compare them directly or compare different model configurations. A higher spread NPI does not always mean more support for the selected side.",
    disclaimer: "NPI supports decision-making and does not guarantee an outcome.",
  },
  confidence: {
    title: "Confidence Rating",
    ariaLabel: "Learn about Confidence Rating",
    short: "A 0–95 rating based on NPI, projected-edge size, and the model-probability input. It is not win probability.",
    detailed: "Confidence Rating is a 0–95 score based on NPI, the size of the projected edge, and the model-probability input. It describes model conviction. It is not win probability and should not be read as “percent chance to win.” Historical Confidence and Risk remain the values produced by their original model version.",
    disclaimer: "Confidence describes model conviction, not certainty of winning.",
  },
  modelProbability: {
    title: "Model Probability",
    ariaLabel: "Learn about Model Probability",
    short: "The model's estimated likelihood of the displayed selection—a team, OVER, or UNDER. It is different from Confidence Rating.",
    detailed: "Model Probability is the model's estimate for the displayed selection—a team, OVER, or UNDER. It is not a guarantee or a fully calibrated probability. Spreads use margin simulations, moneylines use a spread-based estimate, and totals use a projected-total estimate rather than a simulation.",
    disclaimer: "Model Probability is an estimate, not a guaranteed outcome.",
  },
  projectedEdge: {
    title: "Projected Edge",
    ariaLabel: "Learn about Projected Edge",
    short: "A comparison between the model and a reference for that market—not a promise of profit.",
    detailed: "Projected Edge compares the model with a reference point for that market. Spread and moneyline edges are measured in percentage points; total edges are measured in scoring points. It is not a universal expected-profit figure.",
    disclaimer: "An edge estimate does not guarantee value at a changed sportsbook price.",
  },
  risk: {
    title: "Risk Level",
    ariaLabel: "Learn about Risk Level",
    short: "Based on Confidence Rating: Low at 80 or higher, Medium from 65 to 79.99, and High below 65. It is not a measure of personal bankroll risk.",
    detailed: "Risk Level is currently derived from Confidence Rating. It is not an independent bankroll-risk or volatility model, and it does not measure how much you can afford to wager.",
    disclaimer: "Users remain responsible for wagering decisions.",
  },
};

export const npiMarketEducation = [
  { market: "spread", title: "Spread NPI", description: "Combines the spread line, scoring context, and fixed model rules. Its underlying score is home-oriented; Model Probability is adjusted for the selected side." },
  { market: "moneyline", title: "Moneyline NPI", description: "Compares the model’s win estimate with the sportsbook’s implied probability after accounting for the odds margin (vig)." },
  { market: "total", title: "Total NPI", description: "Measures how far the posted game total is from the model’s scoring baseline for that sport." },
] as const;

export const projectedEdgeEducation = [
  { market: "spread", title: "Spread", description: "The percentage-point difference from a 50% chance to cover reference." },
  { market: "moneyline", title: "Moneyline", description: "The percentage-point difference from the sportsbook’s implied probability with the odds margin (vig) removed." },
  { market: "total", title: "Total", description: "The scoring-point difference between the model’s projection and the posted game total." },
] as const;

export const npiReportingNote = "Numeric NPI reporting ranges are not calibrated strength levels. Scores from different markets or model configurations should not be directly compared.";
export const npiBandsExplanation = "There are no named NPI strength levels. Numeric ranges are reporting groups, not proven labels such as Weak, Strong, or Elite. A score range should not be treated as a level of pick strength.";
export const npiBandsNotice = "Any future strength levels will need enough completed results to show that they are stable for each sport, market, and model.";
export const riskThresholds = [
  { title: "Low", description: "Confidence Rating 80 or higher." },
  { title: "Medium", description: "Confidence Rating 65 through 79.99." },
  { title: "High", description: "Confidence Rating below 65." },
] as const;
export const dashboardSequence = [
  "The system checks the latest game and market information.",
  "It calculates the model’s signals separately for each market.",
  "Picks without the required information are left out.",
  "Eligible picks are ranked within their model.",
  "The supported pick for each game and market appears on the dashboard.",
  "After a game is complete, the result is recorded for Performance reporting.",
] as const;
export const responsibleInterpretation = [
  "Model numbers are estimates, not guarantees.",
  "Sports outcomes are uncertain.",
  "Past results do not guarantee future results.",
  "Compare picks only in the same market context.",
  "Check current sportsbook prices; lines and odds can change.",
  "You are responsible for your own wagering decisions.",
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
