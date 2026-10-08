import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { CUSTOMER_SUPPORT_EMAIL, CUSTOMER_SUPPORT_MAILTO } from "../../src/data/customerSupport";
import { LegalPage } from "../../src/pages/LegalPage";

describe("public support identity", () => {
  it("centralizes the intended public mailbox and mailto", () => {
    expect(CUSTOMER_SUPPORT_EMAIL).toBe("owner@bearahandllc.com");
    expect(CUSTOMER_SUPPORT_MAILTO).toBe("mailto:owner@bearahandllc.com");
  });

  it("uses the shared support address on the public support page", () => {
    render(<MemoryRouter initialEntries={["/support"]}><LegalPage /></MemoryRouter>);
    expect(screen.getByRole("link", { name: "Email support (opens your email application)" })
      .getAttribute("href")).toBe(CUSTOMER_SUPPORT_MAILTO);
    expect(screen.getByText(/mailbox and staffing must be confirmed/)).toBeTruthy();
  });

  it("retains the legal draft without adding a support action on other legal pages", () => {
    render(<MemoryRouter initialEntries={["/privacy"]}><LegalPage /></MemoryRouter>);
    expect(screen.queryByRole("link", { name: /Email support/ })).toBeNull();
    expect(screen.getByText(/Operational draft for attorney review/)).toBeTruthy();
  });
});
