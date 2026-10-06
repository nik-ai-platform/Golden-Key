import { describe, expect, it } from "vitest";

import {
  formatProductDate,
  formatAmericanOdds,
  formatConfidence,
  formatNpi,
  formatProductTime,
  parseProductDate,
  productDateKey,
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

  describe("unavailable historical numeric metrics", () => {
    it.each([null, Number.NaN, Number.POSITIVE_INFINITY, Number.NEGATIVE_INFINITY])(
      "formats %s without exposing invalid numeric text",
      (value) => {
        expect(formatNpi(value)).toBe("Unavailable");
        expect(formatConfidence(value)).toBe("Not rated");
        expect(formatAmericanOdds(value)).toBeNull();
      },
    );
    it("preserves valid historical metrics and rejects a zero betting price", () => {
      expect(formatNpi(154.5)).toBe("154.5 / 200");
      expect(formatConfidence(83)).toBe("83.0%");
      expect(formatAmericanOdds(-110)).toBe("-110");
      expect(formatAmericanOdds(120)).toBe("+120");
      expect(formatAmericanOdds(0)).toBeNull();
    });
  });

  it("uses Eastern Standard Time in winter", () => {
    expect(formatProductDate("2026-12-12T19:30:00")).toBe("Sat, Dec 12 • 2:30 PM EST");
  });

  it("uses the shared parser for time-only formatting", () => {
    expect(formatProductTime("2026-09-12T19:30:00")).toBe("3:30 PM EDT");
  });

  it("uses Eastern calendar dates across the UTC midnight boundary", () => {
    expect(productDateKey("2026-09-07T00:30:00")).toBe("2026-09-06");
    expect(productDateKey("2026-09-07T04:00:00")).toBe("2026-09-07");
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