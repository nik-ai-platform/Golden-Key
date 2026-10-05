import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { MobileNav } from "../../src/components/MobileNav";

function Location() {
  return <span data-testid="location">{useLocation().pathname}</span>;
}

describe("MobileNav", () => {
  it("keeps all destinations accessible in a horizontally scrollable row", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <MobileNav />
        <Location />
      </MemoryRouter>,
    );

    const navigation = container.querySelector(".MuiBottomNavigation-root");
    const navigationStyle = getComputedStyle(navigation!);
    expect(navigationStyle.overflowX).toBe("auto");
    expect(navigationStyle.overflowY).toBe("hidden");
    expect(navigationStyle.justifyContent).toBe("flex-start");
    expect(navigationStyle.scrollbarWidth).toBe("none");
    expect(navigationStyle.height).toBe("58px");
    expect(navigationStyle.minHeight).toBe("58px");
    expect(screen.getByTestId("mobile-navigation-shell").dataset.safeArea).toBe("bottom");

    const destinations = [
      ["Dashboard", "/dashboard"],
      ["Games", "/games"],
      ["Saved Picks", "/saved-picks"],
      ["Parlays", "/parlays"],
      ["Performance", "/performance"],
      ["Profile", "/profile"],
    ];
    for (const [label] of destinations) {
      const itemStyle = getComputedStyle(screen.getByRole("button", { name: label }));
      expect(itemStyle.minWidth).toBe("68px");
      expect(itemStyle.flexShrink).toBe("0");
      expect(itemStyle.minHeight).toBe("58px");
      expect(Number.parseFloat(itemStyle.minHeight)).toBeGreaterThanOrEqual(44);
    }
    expect(screen.getByRole("button", { name: "Dashboard" }).getAttribute("aria-current")).toBe("page");

    for (const [label, path] of destinations) {
      fireEvent.click(screen.getByRole("button", { name: label }));
      expect(screen.getByTestId("location").textContent).toBe(path);
      expect(screen.getByRole("button", { name: label }).getAttribute("aria-current")).toBe("page");
      const selectedLabel = screen.getByRole("button", { name: label }).querySelector(".MuiBottomNavigationAction-label")!;
      expect(getComputedStyle(selectedLabel).fontSize).toBe("10.24px");
    }
  });
});
