import React from "react";
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import DashboardPage from "../../app/dashboard/page";
import GamesPage from "../../app/games/page";
import NPIIndicator from "../../components/NPIIndicator";
import AIAnalysisPanel from "../../components/AIAnalysisPanel";
import PortfolioPage from "../../app/portfolio/page";

class ResizeObserverMock {
  observe() {
    return undefined;
  }
  unobserve() {
    return undefined;
  }
  disconnect() {
    return undefined;
  }
}

if (!("ResizeObserver" in globalThis)) {
  // Recharts uses ResizeObserver in ResponsiveContainer under jsdom tests.
  (globalThis as typeof globalThis & { ResizeObserver: typeof ResizeObserverMock }).ResizeObserver = ResizeObserverMock;
}

describe("frontend command center", () => {
  it("dashboard loads", () => {
    render(<DashboardPage />);
    expect(screen.getByText("Golden Key Dashboard")).toBeTruthy();
    expect(screen.getByText("Top NPI Scores")).toBeTruthy();
  });

  it("predictions display on games page", () => {
    render(<GamesPage />);
    expect(screen.getByText("Games Intelligence")).toBeTruthy();
    expect(screen.getByText("Celtics ATS")).toBeTruthy();
  });

  it("npi indicator renders", () => {
    render(<NPIIndicator score={87} label="NPI SCORE" />);
    expect(screen.getByText("NPI SCORE")).toBeTruthy();
    expect(screen.getByText("Strong Value")).toBeTruthy();
  });

  it("ai explanations appear", () => {
    render(<AIAnalysisPanel reasons={["Defense advantage", "Market undervaluation", "Simulation edge"]} mainRisk="Injury uncertainty" />);
    expect(screen.getByText("Golden Key Analysis")).toBeTruthy();
    expect(screen.getByText("Main Risk:", { exact: false })).toBeTruthy();
  });

  it("portfolio updates render", () => {
    render(<PortfolioPage />);
    expect(screen.getByText("Golden Key Portfolio")).toBeTruthy();
    expect(screen.getByText("8.5%")).toBeTruthy();
  });

  it("mobile layouts still render key content", () => {
    Object.defineProperty(window, "innerWidth", { value: 390, configurable: true });
    render(<DashboardPage />);
    expect(screen.getByText("Main command center for opportunities, intelligence, and performance.")).toBeTruthy();
  });
});
