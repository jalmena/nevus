import { describe, expect, it } from "vitest";
import i18n, { supportedLanguages } from "@/lib/i18n";
import en from "@/lib/i18n/locales/en.json";
import es from "@/lib/i18n/locales/es.json";
import pt from "@/lib/i18n/locales/pt.json";

const catalogues: Record<string, unknown> = { en, es, pt };
const PLURAL = /_(zero|one|two|few|many|other)$/;

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
  it("exist for every supported language, each named in every language", () => {
    for (const code of supportedLanguages) {
      expect(catalogues[code], code).toBeDefined();
      for (const other of supportedLanguages)
        expect(leaves(catalogues[other]).get(`languages.${code}`), `${other}: ${code}`).toBeTruthy();
    }
  });

  it("say the same things in every language, with the same placeholders", () => {
    const english = leaves(en);
    const stems = new Set([...english.keys()].map((key) => key.replace(PLURAL, "")));
    for (const code of supportedLanguages.filter((c) => c !== "en")) {
      const texts = leaves(catalogues[code]);
      expect(new Set([...texts.keys()].map((key) => key.replace(PLURAL, ""))), code).toEqual(stems);
      for (const [key, text] of texts) {
        expect(text.trim(), `${code}: ${key}`).not.toBe("");
        const stem = key.replace(PLURAL, "");
        const reference = english.get(key) ?? english.get(`${stem}_other`) ?? english.get(stem);
        expect(reference, `${code}: ${key} has no English counterpart`).toBeDefined();
        expect(placeholders(text), `${code}: ${key}`).toEqual(placeholders(reference ?? ""));
      }
    }
  });

  it("pluralise Portuguese", async () => {
    await i18n.changeLanguage("pt");
    expect(i18n.t("sessions.marksCount", { count: 1 })).toBe("1 marca");
    expect(i18n.t("sessions.marksCount", { count: 3 })).toBe("3 marcas");
    expect(i18n.t("push.devices", { count: 0 })).toBe("Ainda nenhum aparelho seu está subscrito.");
    expect(document.documentElement.lang).toBe("pt");
    await i18n.changeLanguage("en");
  });
});
