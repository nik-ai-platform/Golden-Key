import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DashboardHero } from "../../src/components/DashboardHero";
import { ThemeModeProvider } from "../../src/theme/ThemeModeProvider";
import { styleAtBreakpoint } from "./responsiveStyles";

describe("DashboardHero", () => {
  it("keeps its intelligence summary scannable with editorial and data typography", () => {
    render(
      <ThemeModeProvider>
        <DashboardHero predictionCount={24} />
      </ThemeModeProvider>,
    );

    expect(screen.getByTestId("dashboard-hero")).toBeTruthy();
    expect(screen.getByText("Today's edge").classList.contains("gk-editorial")).toBe(true);
    const count = screen.getByTestId("active-prediction-count");
    expect(count.textContent).toBe("24 active predictions");
    expect(count.classList.contains("gk-data")).toBe(true);
    expect(screen.getByText(/Production-model opportunities/)).toBeTruthy();
    const heading = screen.getByText("Today's edge");
    expect(styleAtBreakpoint(heading, 0, "font-size")).toBe("2.5rem");
    expect(styleAtBreakpoint(heading, 600, "font-size")).toBe("3rem");
  });
});