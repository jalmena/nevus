/** A date as people say it: "13 Oct", with the year only when it is not this one. */
export function shortDate(locale: string | undefined, value: string | Date, now = new Date()): string {
  const date =
    typeof value === "string" ? new Date(value.length === 10 ? `${value}T12:00:00` : value) : value;
  const sameYear = date.getFullYear() === now.getFullYear();
  return new Intl.DateTimeFormat(locale, {
    day: "numeric",
    month: "short",
    ...(sameYear ? {} : { year: "numeric" }),
  }).format(date);
}
