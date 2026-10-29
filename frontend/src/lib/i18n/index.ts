import i18n from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import { initReactI18next } from "react-i18next";
import ar from "./locales/ar.json";
import ca from "./locales/ca.json";
import de from "./locales/de.json";
import en from "./locales/en.json";
import es from "./locales/es.json";
import eu from "./locales/eu.json";
import fr from "./locales/fr.json";
import gl from "./locales/gl.json";
import hi from "./locales/hi.json";
import id from "./locales/id.json";
import it from "./locales/it.json";
import ja from "./locales/ja.json";
import ko from "./locales/ko.json";
import nl from "./locales/nl.json";
import pl from "./locales/pl.json";
import pt from "./locales/pt.json";
import ru from "./locales/ru.json";
import tr from "./locales/tr.json";
import zh from "./locales/zh.json";

/**
 * The languages, in the chooser's order: English first, then Spanish and the other languages of Spain, then
 * the rest of Europe, then further out. The backend keeps the same list (`nevus/languages.py`).
 */
export const supportedLanguages = [
  "en", "es", "ca", "gl", "eu", "pt", "fr", "it", "de", "nl", "pl", "ru", "tr", "id", "zh", "ja", "ko", "hi", "ar",
] as const; // prettier-ignore
export type Language = (typeof supportedLanguages)[number];

/** What each language calls itself: a reader looking for their own language recognises it written their way. */
export const languageNames: Record<Language, string> = {
  en: "English",
  es: "Español",
  ca: "Català",
  gl: "Galego",
  eu: "Euskara",
  pt: "Português",
  fr: "Français",
  it: "Italiano",
  de: "Deutsch",
  nl: "Nederlands",
  pl: "Polski",
  ru: "Русский",
  tr: "Türkçe",
  id: "Bahasa Indonesia",
  zh: "中文",
  ja: "日本語",
  ko: "한국어",
  hi: "हिन्दी",
  ar: "العربية",
};

/** The languages written right to left. */
export const rtlLanguages: readonly Language[] = ["ar"];

export function isLanguage(code: string | undefined): code is Language {
  return (supportedLanguages as readonly string[]).includes(code ?? "");
}

const catalogues = { ar, ca, de, en, es, eu, fr, gl, hi, id, it, ja, ko, nl, pl, pt, ru, tr, zh } as const;

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: Object.fromEntries(
      Object.entries(catalogues).map(([code, translation]) => [code, { translation }]),
    ),
    supportedLngs: [...supportedLanguages],
    fallbackLng: "en",
    interpolation: { escapeValue: false },
    detection: {
      order: ["localStorage", "navigator"],
      caches: ["localStorage"],
      lookupLocalStorage: "nevus.language",
    },
  });

// Assistive technology reads the page in the document's language, and the page runs the language's way:
// keep both the interface's.
function announce(language: string) {
  if (typeof document === "undefined") return;
  document.documentElement.lang = language;
  document.documentElement.dir = rtlLanguages.includes(language as Language) ? "rtl" : "ltr";
}
i18n.on("languageChanged", announce);
if (i18n.resolvedLanguage) announce(i18n.resolvedLanguage);

export default i18n;
