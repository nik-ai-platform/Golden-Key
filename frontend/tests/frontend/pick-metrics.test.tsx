import { render, screen, within } from "@testing-library/react";
import { ThemeProvider } from "@mui/material";
import { describe, expect, it } from "vitest";

import { PickMetrics } from "../../src/components/PickMetrics";
import { createAppTheme } from "../../src/theme";

function renderMetrics(
  overrides: Partial<React.ComponentProps<typeof PickMetrics>> = {},
  mode: "light" | "dark" = "light",
) {
  return render(
    <ThemeProvider theme={createAppTheme(mode)}>
      <PickMetrics
        npi={180}
        confidence={82.4}
        simulationProbability={64.2}
        projectedEdge={6.2}
        riskLevel="LOW"
        {...overrides}
      />
    </ThemeProvider>,
  );
}

describe("compact pick metrics", () => {
  it("renders formatted model values without exposing raw risk text", () => {
    renderMetrics();
    const metrics = screen.getByTestId("pick-metrics");

    expect(within(metrics).getByText("180.0 / 200")).toBeTruthy();
    expect(within(metrics).getByText("82.4%")).toBeTruthy();
    expect(within(metrics).getByText("64.2%")).toBeTruthy();
    expect(within(metrics).getByText("+6.2%")).toBeTruthy();
    expect(within(metrics).getByText("Low")).toBeTruthy();
    expect(within(metrics).queryByText("LOW")).toBeNull();
    expect(within(metrics).getByText("Edge")).toBeTruthy();
    expect(within(metrics).queryByText("Projected Edge")).toBeNull();
  });

  it.each([
    [-3.1, "-3.1%"],
    [0, "0.0%"],
  ])("formats edge %s as %s", (projectedEdge, expected) => {
    renderMetrics({ projectedEdge });
    expect(screen.getByText(expected)).toBeTruthy();
  });

  it("uses an em dash for each unavailable supporting metric", () => {
    renderMetrics({
      confidence: null,
      simulationProbability: null,
      projectedEdge: null,
      riskLevel: null,
    });

    expect(screen.getAllByText("—")).toHaveLength(4);
    expect(screen.queryByText(/null|undefined|NaN|Not rated/i)).toBeNull();
  });

  it("renders readable semantic risk text in dark mode", () => {
    renderMetrics({ riskLevel: "HIGH" }, "dark");

    expect(screen.getByText("High")).toBeTruthy();
    expect(screen.queryByText("HIGH")).toBeNull();
  });
});