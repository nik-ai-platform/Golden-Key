import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DashboardHero } from "../../src/components/DashboardHero";
import { ThemeModeProvider } from "../../src/theme/ThemeModeProvider";
import { styleAtBreakpoint } from "./responsiveStyles";
describe("DashboardHero", () => {
  it("keeps its editorial headline and picks action without redundant slate metadata", () => {
    render(
      <ThemeModeProvider>
        <DashboardHero />
      </ThemeModeProvider>,
    );

    expect(screen.getByTestId("dashboard-hero")).toBeTruthy();
    expect(screen.getByText("Bear A Hand Sports").classList.contains("gk-editorial")).toBe(true);
    expect(screen.queryByText("Upcoming matchups")).toBeNull();
    expect(screen.queryByText("Reported model version")).toBeNull();
    expect(screen.queryByTestId("dashboard-hero-metadata")).toBeNull();
    const heading = screen.getByRole("heading", { name: "THE GAME. THE DATA. YOUR EDGE." });
    expect(styleAtBreakpoint(heading, 0, "font-size")).toBe("2.6rem");
    expect(styleAtBreakpoint(heading, 600, "font-size")).toBe("3.4rem");
    expect(screen.getByRole("img").getAttribute("src")).toBe("/bear-hero.jpg");
    expect(screen.queryByText(/68%/)).toBeNull();
    expect(screen.getByRole("link", { name: "Explore picks" }).getAttribute("href")).toBe("#upcoming-games-heading");
  });
});