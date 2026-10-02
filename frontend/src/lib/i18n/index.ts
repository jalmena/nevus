import i18n from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import { initReactI18next } from "react-i18next";
import en from "./locales/en.json";
import es from "./locales/es.json";

export const supportedLanguages = ["en", "es"] as const;
export type Language = (typeof supportedLanguages)[number];

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: { en: { translation: en }, es: { translation: es } },
    supportedLngs: [...supportedLanguages],
    fallbackLng: "en",
    interpolation: { escapeValue: false },
    detection: {
      order: ["localStorage", "navigator"],
      caches: ["localStorage"],
      lookupLocalStorage: "nevus.language",
    },
  });

// Assistive technology reads the page in the document's language: keep it the interface's.
function announce(language: string) {
  if (typeof document !== "undefined") document.documentElement.lang = language;
}
i18n.on("languageChanged", announce);
if (i18n.resolvedLanguage) announce(i18n.resolvedLanguage);

export default i18n;
