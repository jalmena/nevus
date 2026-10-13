/** The one date format of the interface: "13 Oct 2026", in the person's language. */
export function shortDate(locale: string | undefined, value: string | Date): string {
  const date =
    typeof value === "string" ? new Date(value.length === 10 ? `${value}T12:00:00` : value) : value;
  return new Intl.DateTimeFormat(locale, { day: "numeric", month: "short", year: "numeric" }).format(date);
}

/** The same date with the time of day, for things that happen more than once a day. */
export function shortDateTime(locale: string | undefined, value: string | Date): string {
  const date = typeof value === "string" ? new Date(value) : value;
  return `${shortDate(locale, date)}, ${new Intl.DateTimeFormat(locale, { timeStyle: "short" }).format(date)}`;
}
