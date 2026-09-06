import { describe, expect, it } from "vitest";

import {
  formatProductDate,
  formatProductTime,
  parseProductDate,
} from "../src/utils/productFormat";

describe("sports datetime formatting", () => {
  it.each([
    "2026-09-12T19:30:00",
    "2026-09-12T19:30:00Z",
    "2026-09-12T19:30:00+00:00",
    "2026-09-12T15:30:00-04:00",
  ])("formats %s as the same EDT kickoff", (timestamp) => {
    expect(formatProductDate(timestamp)).toBe("Sat, Sep 12 • 3:30 PM EDT");
  });

  it("uses Eastern Standard Time in winter", () => {
    expect(formatProductDate("2026-12-12T19:30:00")).toBe("Sat, Dec 12 • 2:30 PM EST");
  });

  it("uses the shared parser for time-only formatting", () => {
    expect(formatProductTime("2026-09-12T19:30:00")).toBe("3:30 PM EDT");
  });

  it.each([
    ["2026-09-12T16:00:00", "12:00 PM EDT"],
    ["2026-09-12T19:30:00", "3:30 PM EDT"],
    ["2026-09-12T23:30:00", "7:30 PM EDT"],
    ["2026-09-13T04:00:00", "12:00 AM EDT"],
    ["2026-09-10T04:15:00", "12:15 AM EDT"],
  ])("formats known production kickoff %s", (timestamp, expected) => {
    expect(formatProductTime(timestamp)).toBe(expected);
  });

  it("returns graceful fallbacks for invalid and missing timestamps", () => {
    expect(parseProductDate("not-a-date")).toBeNull();
    expect(formatProductDate("not-a-date")).toBe("Date unavailable");
    expect(formatProductDate(undefined)).toBe("Date unavailable");
    expect(formatProductTime("")).toBe("Time unavailable");
    expect(formatProductTime(null)).toBe("Time unavailable");
  });
});