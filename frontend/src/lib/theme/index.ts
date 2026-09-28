export type Theme = "system" | "light" | "dark";

/** Themes are tokens on the root element; the brand block stays dark regardless (see tokens.css). */
export function applyTheme(theme: string): void {
  const root = document.documentElement;
  if (theme === "light" || theme === "dark") root.dataset.theme = theme;
  else delete root.dataset.theme;
}
