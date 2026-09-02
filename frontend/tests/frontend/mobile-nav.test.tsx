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

    const destinations = [
      "Dashboard",
      "Games",
      "Saved Picks",
      "Parlays",
      "Performance",
      "Profile",
    ];
    for (const label of destinations) {
      const itemStyle = getComputedStyle(screen.getByRole("button", { name: label }));
      expect(itemStyle.minWidth).toBe("72px");
      expect(itemStyle.flexShrink).toBe("0");
    }

    fireEvent.click(screen.getByRole("button", { name: "Profile" }));
    expect(screen.getByTestId("location").textContent).toBe("/profile");
  });
});
