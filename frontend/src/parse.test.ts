import { describe, expect, it } from "vitest";
import { chatText } from "./parse";

describe("chatText", () => {
  it("keeps short quoted snippets", () => {
    const text = "Regarde :\n```python\nx = 1\n```\nCool !";
    expect(chatText(text, null, "fr").text).toBe(text);
  });

  it("hides whole files pasted in old replies", () => {
    const file = Array.from({ length: 20 }, (_, i) => `l${i}`).join("\n");
    expect(chatText("Voici :\n```python\n" + file + "\n```\nFini", null, "fr").text).toBe("Voici :\n\nFini");
  });

  it("hides a code block that is still streaming", () => {
    expect(chatText("Je commence\n```python\nimport py", null, "fr").text).toBe("Je commence");
  });

  it("labels what Pix is doing", () => {
    expect(chatText("", "test_game", "fr").activity).toBe("🧪 Je teste le jeu…");
    expect(chatText("", "outil_inconnu", "fr").activity).toBe("🛠️ Je travaille…");
    expect(chatText("", null, "fr").activity).toBeNull();
  });

  it("labels tools in the UI language", () => {
    expect(chatText("", "test_game", "en").activity).toBe("🧪 Testing the game…");
    expect(chatText("", "read", "pl").activity).toBe("📖 Czytam twój kod…");
  });
});
