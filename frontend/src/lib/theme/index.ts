export type Theme = "system" | "light" | "dark";

/** The paper of each theme (tokens.css), for the browser's own bar, which cannot read the tokens. */
const PAPER = { light: "#F6F1EA", dark: "#17161A" } as const;

/** Themes are tokens on the root element; the brand block stays dark regardless (see tokens.css). */
export function applyTheme(theme: string): void {
  const root = document.documentElement;
  if (theme === "light" || theme === "dark") root.dataset.theme = theme;
  else delete root.dataset.theme;
  // index.html has one theme-color per colour scheme; a theme fixed by the person overrides both.
  for (const meta of document.querySelectorAll<HTMLMetaElement>('meta[name="theme-color"]')) {
    const scheme = meta.media.includes("dark") ? "dark" : "light";
    meta.content = PAPER[theme === "light" || theme === "dark" ? theme : scheme];
  }
}
