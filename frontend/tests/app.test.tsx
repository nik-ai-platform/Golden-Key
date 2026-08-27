import { describe, it, expect } from "vitest";

import React from "react";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import DashboardPage from "../app/dashboard/page";
import { PredictionCard } from "../components/predictions/PredictionCard";
import { NotificationCenter } from "../components/notifications/NotificationCenter";
import { ProductExperiencePage } from "../src/pages/ProductExperiencePage";

describe("frontend UI scaffold", () => {
  it("renders dashboard content", () => {
    render(<DashboardPage />);
    expect(screen.getByText("Golden Key Dashboard")).toBeTruthy();
  });

  it("renders prediction card", () => {
    render(<PredictionCard />);
    expect(screen.getByText("Golden Key Prediction")).toBeTruthy();
  });

  it("renders notification center", () => {
    render(<NotificationCenter />);
    expect(screen.getByText("Notifications")).toBeTruthy();
  });

  it("renders the integrated product experience shell", () => {
    render(
      <MemoryRouter>
        <ProductExperiencePage />
      </MemoryRouter>,
    );
    expect(screen.getByText("Product Experience Preview")).toBeTruthy();
  });
});
