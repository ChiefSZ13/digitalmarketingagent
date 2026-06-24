export function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function moneyRange(
  low: number | null,
  high: number | null,
  currency: string,
): string {
  if (low === null && high === null) {
    return "Unknown";
  }
  const formatter = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  });
  if (low !== null && high !== null) {
    return `${formatter.format(low)} - ${formatter.format(high)}`;
  }
  if (low !== null) {
    return `From ${formatter.format(low)}`;
  }
  return `Up to ${formatter.format(high ?? 0)}`;
}

export function compactNumber(value: number | null): string {
  if (value === null) {
    return "0";
  }
  return new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

export function titleize(value: string): string {
  return value
    .replaceAll("_", " ")
    .split(" ")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
