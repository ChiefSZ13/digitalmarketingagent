export function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function titleize(value: string): string {
  return value
    .replaceAll("_", " ")
    .split(" ")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
