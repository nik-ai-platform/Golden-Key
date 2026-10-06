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
    await screen.findByRole("heading", { level: 1, name: "How to read a pick" });
    for (const name of ["What the numbers mean", "Why NPI depends on the market", "About NPI score ranges", "What “projected edge” compares", "How Risk Level is labeled", "How picks are chosen", "A note on uncertainty"]) {
      expect(screen.getByRole("region", { name })).toBeTruthy();
    }
    const numbers = screen.getByRole("region", { name: "What the numbers mean" });
    expect(numbers.textContent).toContain("NPI is a model score, not a chance to win");
    expect(numbers.textContent).toContain("Confidence is not win probability");
    expect(numbers.textContent).toContain("not yet presented as fully calibrated probabilities");
    const npi = screen.getByRole("region", { name: "Why NPI depends on the market" });
    for (const name of ["Spread NPI", "Moneyline NPI", "Total NPI"]) {
      expect(within(npi).getByRole("heading", { name })).toBeTruthy();
    }
    expect(npi.textContent).toContain("home-oriented");
    expect(npi.textContent).toContain("odds margin (vig)");
    expect(npi.textContent).toContain("scoring baseline for that sport");
    expect(npi.textContent).toContain("do not compare them directly");
    const bands = screen.getByRole("region", { name: "About NPI score ranges" });
    expect(bands.textContent).toContain("There are no named NPI strength levels");
    expect(bands.textContent).toContain("not proven labels such as Weak, Strong, or Elite");
    expect(within(bands).queryByRole("heading", { name: /Weak|Strong|Elite/ })).toBeNull();
    expect(bands.textContent).toContain("enough completed results");
    expect(screen.getByRole("region", { name: "What the numbers mean" }).textContent).toContain("percent chance to win");
    expect(screen.getByRole("region", { name: "What the numbers mean" }).textContent).toContain("not yet presented as fully calibrated probabilities");
    const edge = screen.getByRole("region", { name: "What “projected edge” compares" });
    for (const text of ["50% chance to cover reference", "implied probability with the odds margin (vig) removed", "scoring-point difference", "not a universal expected-profit figure"]) {
      expect(edge.textContent).toContain(text);
    }
    const risk = screen.getByRole("region", { name: "How Risk Level is labeled" });
    for (const text of ["80 or higher", "65 through 79.99", "below 65"]) {
      expect(risk.textContent).toContain(text);
    }
    expect(screen.getByRole("region", { name: "What the numbers mean" }).textContent).toContain("not a separate measure of volatility or personal bankroll risk");
    const sequence = screen.getByRole("region", { name: "How picks are chosen" });
    expect(within(sequence).getByRole("list").tagName).toBe("OL");
    expect(within(sequence).getAllByRole("listitem")).toHaveLength(6);
    expect(within(sequence).getByText(/latest game and market information/)).toBeTruthy();
    const responsible = screen.getByRole("region", { name: "A note on uncertainty" });
    expect(within(responsible).getAllByRole("listitem")).toHaveLength(6);
    for (const text of ["not guarantees", "uncertain", "Past results do not guarantee future results", "same market context", "lines and odds can change", "responsible for your own wagering decisions"]) {
      expect(responsible.textContent).toContain(text);
    }
    const pageNav = screen.getByRole("navigation", { name: "On this page" });
    expect(within(pageNav).getByRole("link", { name: "The numbers" }).getAttribute("href")).toBe("#the-numbers");
    expect(within(pageNav).getByRole("link", { name: "How picks are chosen" }).getAttribute("href")).toBe("#how-picks-are-chosen");
    expect(screen.getByRole("main").textContent).not.toMatch(/NPI TOP \d|Confidence %|score out of 200|higher means stronger/i);
  });

  it("does not expose the education route to signed-out customers", async () => {
    renderEducation(false);
    expect(await screen.findByRole("heading", { name: "Sign in required" })).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "How to read a pick" })).toBeNull();
  });

  it("provides desktop and mobile drawer access without a seventh bottom destination", async () => {
    renderEducation();
    await screen.findByRole("heading", { name: "How to read a pick" });
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
