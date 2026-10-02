/**
 * Memorable names for marks, so "the one on my shoulder" has a handle (an idea from MoleMapper).
 * Calm, neutral words only: nothing that sounds like a judgement about the mark.
 */
const WORDS = {
  en: {
    first: [
      "Quiet",
      "Little",
      "Steady",
      "Patient",
      "Round",
      "Faithful",
      "Gentle",
      "Brave",
      "Curious",
      "Sunny",
      "Calm",
      "Tiny",
    ],
    second: [
      "Pebble",
      "Comet",
      "Button",
      "Acorn",
      "Harbour",
      "Lantern",
      "Compass",
      "Meadow",
      "Pepper",
      "Cocoa",
      "Island",
      "Sparrow",
    ],
    order: "first second",
  },
  es: {
    first: [
      "Botón",
      "Cometa",
      "Bellota",
      "Faro",
      "Brújula",
      "Grano",
      "Islote",
      "Gorrión",
      "Cacao",
      "Guijarro",
      "Lucero",
      "Puerto",
    ],
    second: [
      "tranquilo",
      "pequeño",
      "fiel",
      "paciente",
      "redondo",
      "valiente",
      "curioso",
      "sereno",
      "risueño",
      "discreto",
      "leal",
      "atento",
    ],
    order: "first second",
  },
} as const;

export function suggestName(language: string, random: () => number = Math.random): string {
  const words = WORDS[language === "es" ? "es" : "en"];
  const pick = (list: readonly string[]) => list[Math.floor(random() * list.length)] ?? list[0] ?? "";
  return `${pick(words.first)} ${pick(words.second)}`;
}
