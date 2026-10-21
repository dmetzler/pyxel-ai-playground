import { describe, expect, it } from "vitest";
import { LANGS, MESSAGES, detectLang, translate } from "./i18n";
import { STARTER_CODES, WELCOME_MESSAGES } from "./starter";

describe("dictionaries", () => {
  const frKeys = Object.keys(MESSAGES.fr).sort();

  it.each(LANGS)("%s has exactly the keys of fr, all filled in", (lang) => {
    expect(Object.keys(MESSAGES[lang]).sort()).toEqual(frKeys);
    for (const key of frKeys) expect(MESSAGES[lang][key as keyof typeof MESSAGES.fr].trim()).not.toBe("");
  });

  it.each(LANGS)("%s has a starter game and a welcome message", (lang) => {
    expect(STARTER_CODES[lang]).toContain("pyxel.run(");
    // pyxel.text only draws ASCII.
    expect(STARTER_CODES[lang]).toMatch(/^[\x00-\x7f]*$/);
    expect(WELCOME_MESSAGES[lang]).toContain("**Pix**");
  });

  it("fills in placeholders", () => {
    expect(translate("en", "picker.deleteLabel", { name: "Snake" })).toBe("Delete Snake");
    expect(translate("fr", "server.error", { status: 409 })).toBe("Erreur du serveur 409");
  });
});

describe("detectLang", () => {
  it("follows the browser language, French otherwise", () => {
    expect(detectLang("pl-PL")).toBe("pl");
    expect(detectLang("pl")).toBe("pl");
    expect(detectLang("en-US")).toBe("en");
    expect(detectLang("fr-FR")).toBe("fr");
    expect(detectLang("de")).toBe("fr");
    expect(detectLang(undefined)).toBe("fr");
  });
});
