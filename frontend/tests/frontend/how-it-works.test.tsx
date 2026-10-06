import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AuthContext } from "../../src/auth/AuthContextDefinition";
import { MetricInfoControl } from "../../src/components/MetricInfoControl";
import { predictionMetricEducation, type PredictionMetric } from "../../src/data/predictionMetricEducation";
import { AppRouter } from "../../src/routes/AppRouter";
import { ThemeModeProvider } from "../../src/theme/ThemeModeProvider";

vi.mock("../../src/pages/LoginPage", () => ({ LoginPage: () => <h1>Sign in required</h1> }));

const auth = {
  user: { id: 1, email: "user@example.com", username: "user", role: "user" as const },
  isAuthenticated: true, isBootstrapping: false, login: vi.fn(), logout: vi.fn(),
};

function renderEducation(authenticated = true) {
  return render(
    <ThemeModeProvider>
      <AuthContext.Provider value={{ ...auth, isAuthenticated: authenticated }}>
        <MemoryRouter initialEntries={["/how-it-works"]}><AppRouter /></MemoryRouter>
      </AuthContext.Provider>
    </ThemeModeProvider>,
  );
}

describe("customer metric education", () => {
  it("renders the protected route with all required accessible sections", async () => {
    renderEducation();
    await screen.findByRole("heading", { level: 1, name: "How the Intelligence Works" });
    for (const name of ["Nik Power Index (NPI)", "NPI bands", "Model Probability", "Confidence Rating", "Projected Edge", "Risk Level", "How a pick reaches the dashboard", "Responsible interpretation"]) {
      expect(screen.getByRole("region", { name })).toBeTruthy();
    }
    const npi = screen.getByRole("region", { name: "Nik Power Index (NPI)" });
    for (const name of ["Spread NPI", "Moneyline NPI", "Total NPI"]) {
      expect(within(npi).getByRole("heading", { name })).toBeTruthy();
    }
    expect(npi.textContent).toContain("home-oriented");
    expect(npi.textContent).toContain("vig-adjusted implied probability");
    expect(npi.textContent).toContain("sport-specific scoring baseline");
    expect(npi.textContent).toContain("should not be directly compared");
    const bands = screen.getByRole("region", { name: "NPI bands" });
    expect(bands.textContent).toContain("does not currently publish named NPI strength bands");
    expect(bands.textContent).toContain("not proven levels such as Weak, Strong, or Elite");
    expect(within(bands).queryByRole("heading", { name: /Weak|Strong|Elite/ })).toBeNull();
    expect(bands.textContent).toContain("collects settled predictions across each sport and market");
    expect(screen.getByRole("region", { name: "Confidence Rating" }).textContent).toContain("not win probability");
    expect(screen.getByRole("region", { name: "Confidence Rating" }).textContent).toContain("percent chance to win");
    expect(screen.getByRole("region", { name: "Model Probability" }).textContent).toContain("has not yet been presented as a fully calibrated probability");
    const edge = screen.getByRole("region", { name: "Projected Edge" });
    for (const text of ["50% cover benchmark", "vig-free implied probability", "Scoring-point difference", "not a universal expected-profit figure"]) {
      expect(edge.textContent).toContain(text);
    }
    const risk = screen.getByRole("region", { name: "Risk Level" });
    for (const text of ["80 or higher", "65 through 79.99", "below 65", "not an independent bankroll-risk or volatility model"]) {
      expect(risk.textContent).toContain(text);
    }
    const sequence = screen.getByRole("region", { name: "How a pick reaches the dashboard" });
    expect(within(sequence).getByRole("list").tagName).toBe("OL");
    expect(within(sequence).getAllByRole("listitem")).toHaveLength(6);
    const responsible = screen.getByRole("region", { name: "Responsible interpretation" });
    expect(within(responsible).getAllByRole("listitem")).toHaveLength(6);
    for (const text of ["not guarantees", "uncertainty", "does not guarantee future results", "same market context", "lines and odds change", "responsible for wagering decisions"]) {
      expect(responsible.textContent).toContain(text);
    }
    expect(screen.getByRole("main").textContent).not.toMatch(/NPI TOP \d|Confidence %|score out of 200|higher means stronger/i);
  });

  it("does not expose the education route to signed-out customers", async () => {
    renderEducation(false);
    expect(await screen.findByRole("heading", { name: "Sign in required" })).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "How the Intelligence Works" })).toBeNull();
  });

  it("provides desktop and mobile drawer access without a seventh bottom destination", async () => {
    renderEducation();
    await screen.findByRole("heading", { name: "How the Intelligence Works" });
    const desktopLink = screen.getByRole("link", { name: "How It Works" });
    expect(desktopLink.getAttribute("href")).toBe("/how-it-works");
    expect(desktopLink.getAttribute("aria-current")).toBe("page");
    expect(within(screen.getByTestId("mobile-navigation-shell")).getAllByRole("button")).toHaveLength(6);
    fireEvent.click(screen.getByRole("button", { name: "Open navigation" }));
    const mobileLink = await screen.findByRole("link", { name: "How It Works" });
    expect(mobileLink.getAttribute("href")).toBe("/how-it-works");
    expect(mobileLink.getAttribute("aria-current")).toBe("page");
  });

  it.each(Object.keys(predictionMetricEducation) as PredictionMetric[])(
    "%s help has an accessible dialog, education link, and Escape focus restoration",
    async (metric) => {
      render(<MemoryRouter><MetricInfoControl metric={metric} market="spread" /></MemoryRouter>);
      const button = screen.getByRole("button", { name: predictionMetricEducation[metric].ariaLabel });
      button.focus();
      fireEvent.click(button);
      const dialog = await screen.findByRole("dialog", { name: predictionMetricEducation[metric].title });
      const link = within(dialog).getByRole("link", { name: "Learn how all metrics work" });
      expect(link.getAttribute("href")).toBe("/how-it-works");
      expect(button.getAttribute("aria-expanded")).toBe("true");
      link.focus();
      expect(document.activeElement).toBe(link);
      fireEvent.keyDown(link, { key: "Escape" });
      await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
      expect(document.activeElement).toBe(button);
    },
  );
});
