import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DashboardHero } from "../../src/components/DashboardHero";
import { ThemeModeProvider } from "../../src/theme/ThemeModeProvider";
import { styleAtBreakpoint } from "./responsiveStyles";

describe("DashboardHero", () => {
  it("does not invent counts or model versions when the slate is unavailable", () => {
    render(<ThemeModeProvider><DashboardHero matchupCount={null} modelVersions={[]} /></ThemeModeProvider>);
    expect(screen.getByTestId("upcoming-matchup-count").textContent).toBe("Unavailable");
    expect(screen.getByTestId("reported-model-version").textContent).toBe("Unavailable");
  });

  it("keeps zero matchups distinct from unavailable and shows all reported versions", () => {
    render(<ThemeModeProvider><DashboardHero matchupCount={0} modelVersions={["NPI-4.0", "NPI-5.0"]} /></ThemeModeProvider>);
    expect(screen.getByTestId("upcoming-matchup-count").textContent).toBe("0");
    expect(screen.getByTestId("reported-model-version").textContent).toBe("NPI-4.0 · NPI-5.0");
  });

  it("keeps its intelligence summary scannable with editorial and data typography", () => {
    render(
      <ThemeModeProvider>
        <DashboardHero matchupCount={24} modelVersions={["NPI-5.0"]} />
      </ThemeModeProvider>,
    );

    expect(screen.getByTestId("dashboard-hero")).toBeTruthy();
    expect(screen.getByText("Bear A Hand Sports").classList.contains("gk-editorial")).toBe(true);
    const count = screen.getByTestId("upcoming-matchup-count");
    expect(count.textContent).toBe("24");
    expect(count.classList.contains("gk-data")).toBe(true);
    expect(screen.getByTestId("reported-model-version").textContent).toBe("NPI-5.0");
    const metadata = screen.getByTestId("dashboard-hero-metadata");
    expect(styleAtBreakpoint(metadata, 0, "display")).toBe("none");
    expect(styleAtBreakpoint(metadata, 600, "display")).toBe("flex");
    const heading = screen.getByRole("heading", { name: "THE GAME. THE DATA. YOUR EDGE." });
    expect(styleAtBreakpoint(heading, 0, "font-size")).toBe("2.6rem");
    expect(styleAtBreakpoint(heading, 600, "font-size")).toBe("3.4rem");
    expect(screen.getByRole("img").getAttribute("src")).toBe("/bear-hero.jpg");
    expect(screen.queryByText(/68%/)).toBeNull();
    expect(screen.getByRole("link", { name: "Explore picks" }).getAttribute("href")).toBe("#upcoming-games-heading");
  });
});