const productDateOptions: Intl.DateTimeFormatOptions = {
  weekday: "short",
  month: "short",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
};

export function formatProductDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, productDateOptions).format(
    new Date(value),
  );
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