import { fireEvent, render, screen, within } from "@testing-library/react";
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
        market="spread"
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
    expect(within(metrics).getByText("Low")).toBeTruthy();
    expect(within(metrics).queryByText("LOW")).toBeNull();
    expect(within(metrics).queryByText("Projected Edge")).toBeNull();
    expect(within(metrics).queryByText("Edge")).toBeNull();
    expect(within(metrics).queryByText("+6.2 pp")).toBeNull();
  });

  it.each([
    ["Learn about NPI", "Golden Key's 0–200 model-support score."],
    ["Learn about Confidence Rating", "It is not win probability."],
    ["Learn about Model Probability", "distinct from Confidence"],
  ])("opens the %s information control", async (accessibleName, definition) => {
    renderMetrics();

    fireEvent.click(screen.getByRole("button", { name: accessibleName }));

    expect(await screen.findByText(new RegExp(definition, "i"))).toBeTruthy();
  });

  it("keeps the information popover within narrow viewports", async () => {
    renderMetrics();

    fireEvent.click(screen.getByRole("button", { name: "Learn about NPI" }));

    const definition = await screen.findByText(/Golden Key's 0–200 model-support score/i);
    const paper = definition.closest(".MuiPopover-paper");

    expect(paper).toBeTruthy();
    const paperStyles = getComputedStyle(paper as Element);
    expect(paperStyles.maxWidth).toBe(`${window.innerWidth - 32}px`);
    expect(paperStyles.minWidth).not.toBe("340px");
    expect(paperStyles.boxSizing).toBe("border-box");
    expect(paperStyles.overflowWrap).toBe("anywhere");
  });

  it("wraps metric labels only at semantic word boundaries", () => {
    renderMetrics();

    const confidence = screen.getByTestId("metric-label-confidence");
    const modelProbability = screen.getByTestId("metric-label-modelProbability");

    expect(getComputedStyle(confidence).whiteSpace).toBe("nowrap");
    expect(getComputedStyle(modelProbability).whiteSpace).toBe("normal");
    expect(modelProbability.textContent).toBe("Model Probability");

    for (const label of screen.getAllByTestId(/^metric-label-/)) {
      const styles = getComputedStyle(label);
      expect(styles.overflowWrap).toBe("normal");
      expect(styles.wordBreak).toBe("normal");
    }
  });

  it("uses an em dash for each unavailable supporting metric", () => {
    renderMetrics({
      confidence: null,
      simulationProbability: null,
      projectedEdge: null,
      riskLevel: null,
    });

    expect(screen.getAllByText("—")).toHaveLength(3);
    expect(screen.queryByText(/null|undefined|NaN|Not rated/i)).toBeNull();
  });

  it("renders readable semantic risk text in dark mode", () => {
    renderMetrics({ riskLevel: "HIGH" }, "dark");

    expect(screen.getByText("High")).toBeTruthy();
    expect(screen.queryByText("HIGH")).toBeNull();
  });
});