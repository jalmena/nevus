import { describe, expect, it } from "vitest";
import i18n, { languageNames, rtlLanguages, supportedLanguages, type Language } from "@/lib/i18n";
import ar from "@/lib/i18n/locales/ar.json";
import ca from "@/lib/i18n/locales/ca.json";
import de from "@/lib/i18n/locales/de.json";
import en from "@/lib/i18n/locales/en.json";
import es from "@/lib/i18n/locales/es.json";
import eu from "@/lib/i18n/locales/eu.json";
import fr from "@/lib/i18n/locales/fr.json";
import gl from "@/lib/i18n/locales/gl.json";
import hi from "@/lib/i18n/locales/hi.json";
import id from "@/lib/i18n/locales/id.json";
import itLocale from "@/lib/i18n/locales/it.json";
import ja from "@/lib/i18n/locales/ja.json";
import ko from "@/lib/i18n/locales/ko.json";
import nl from "@/lib/i18n/locales/nl.json";
import pl from "@/lib/i18n/locales/pl.json";
import pt from "@/lib/i18n/locales/pt.json";
import ru from "@/lib/i18n/locales/ru.json";
import tr from "@/lib/i18n/locales/tr.json";
import zh from "@/lib/i18n/locales/zh.json";

const catalogues: Record<Language, unknown> = {
  en, es, ca, gl, eu, pt, fr, it: itLocale, de, nl, pl, ru, tr, id, zh, ja, ko, hi, ar,
}; // prettier-ignore
const PLURAL = /_(zero|one|two|few|many|other)$/;

/** The plural categories a language's Intl.PluralRules can return, so every count finds its form. */
function categories(code: Language): string[] {
  const rules = new Intl.PluralRules(code);
  const found = new Set<string>();
  for (const n of [0, 1, 2, 3, 5, 11, 21, 22, 25, 100, 101, 1.5]) found.add(rules.select(n));
  return [...found].sort();
}

function leaves(value: unknown, prefix = ""): Map<string, string> {
  const out = new Map<string, string>();
  if (typeof value === "string") out.set(prefix.slice(0, -1), value);
  else if (value && typeof value === "object") {
    for (const [key, child] of Object.entries(value))
      for (const [k, v] of leaves(child, `${prefix}${key}.`)) out.set(k, v);
  }
  return out;
}

/** Placeholders other than count, which every plural form may use or leave out. */
function placeholders(text: string): string[] {
  return [...text.matchAll(/\{\{(\w+)\}\}/g)]
    .map((m) => m[1] ?? "")
    .filter((name) => name !== "count")
    .sort();
}

describe("the interface catalogues", () => {
  it("exist for every supported language, each with its own name and a direction", () => {
    for (const code of supportedLanguages) {
      expect(catalogues[code], code).toBeDefined();
      expect(languageNames[code], code).toBeTruthy();
    }
    expect(rtlLanguages).toEqual(["ar"]);
  });

  it("say the same things in every language, with the same placeholders and every plural form", () => {
    const english = leaves(en);
    const stems = new Set([...english.keys()].map((key) => key.replace(PLURAL, "")));
    const pluralStems = new Set(
      [...english.keys()].filter((key) => PLURAL.test(key)).map((key) => key.replace(PLURAL, "")),
    );
    for (const code of supportedLanguages.filter((c) => c !== "en")) {
      const texts = leaves(catalogues[code]);
      expect(new Set([...texts.keys()].map((key) => key.replace(PLURAL, ""))), code).toEqual(stems);
      for (const stem of pluralStems)
        for (const category of categories(code))
          expect(texts.get(`${stem}_${category}`), `${code}: ${stem}_${category}`).toBeDefined();
      for (const [key, text] of texts) {
        expect(text.trim(), `${code}: ${key}`).not.toBe("");
        const stem = key.replace(PLURAL, "");
        const reference = english.get(key) ?? english.get(`${stem}_other`) ?? english.get(stem);
        expect(reference, `${code}: ${key} has no English counterpart`).toBeDefined();
        expect(placeholders(text), `${code}: ${key}`).toEqual(placeholders(reference ?? ""));
      }
    }
  });

  it("pluralise Portuguese and run Arabic right to left", async () => {
    await i18n.changeLanguage("pt");
    expect(i18n.t("sessions.marksCount", { count: 1 })).toBe("1 marca");
    expect(i18n.t("sessions.marksCount", { count: 3 })).toBe("3 marcas");
    expect(i18n.t("push.devices", { count: 0 })).toBe("Ainda nenhum aparelho seu está subscrito.");
    expect(document.documentElement.lang).toBe("pt");
    expect(document.documentElement.dir).toBe("ltr");
    await i18n.changeLanguage("ar");
    expect(document.documentElement.dir).toBe("rtl");
    await i18n.changeLanguage("en");
    expect(document.documentElement.dir).toBe("ltr");
  });
});
