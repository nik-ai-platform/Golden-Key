const SPORTS_TIME_ZONE = "America/New_York";
const TIMEZONE_SUFFIX = /(?:Z|[+-]\d{2}:?\d{2})$/i;

const productDateOptions: Intl.DateTimeFormatOptions = {
  weekday: "short",
  month: "short",
  day: "numeric",
  timeZone: SPORTS_TIME_ZONE,
};

const productTimeOptions: Intl.DateTimeFormatOptions = {
  hour: "numeric",
  minute: "2-digit",
  timeZone: SPORTS_TIME_ZONE,
  timeZoneName: "short",
};

export function parseProductDate(value: string | null | undefined): Date | null {
  const timestamp = value?.trim();
  if (!timestamp) return null;

  const date = new Date(TIMEZONE_SUFFIX.test(timestamp) ? timestamp : `${timestamp}Z`);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatProductDate(value: string | null | undefined): string {
  const date = parseProductDate(value);
  if (!date) return "Date unavailable";

  const dateLabel = new Intl.DateTimeFormat("en-US", productDateOptions).format(date);
  return `${dateLabel} • ${formatProductTime(value)}`;
}

export function formatProductTime(value: string | null | undefined): string {
  const date = parseProductDate(value);
  if (!date) return "Time unavailable";
  return new Intl.DateTimeFormat("en-US", productTimeOptions).format(date);
}

export function formatAmericanOdds(value: number | null): string | null {
  if (value == null) return null;
  return value > 0 ? `+${value}` : String(value);
}

export function formatNpi(value: number): string {
  return `${value.toFixed(1)} / 200`;
}

export function formatConfidence(value: number | null): string {
  return value == null ? "Not rated" : `${value.toFixed(1)}%`;
}

export function customerFacingReasoning(value: string | null): string | null {
  if (!value) return null;
  const sanitized = value
    .replace(
      /(?:^|\s)Projected market edge:\s*[+-]?\d+(?:\.\d+)?%?\.(?=\s|$)/gi,
      " ",
    )
    .replace(/\s+/g, " ")
    .trim();
  return sanitized || null;
}