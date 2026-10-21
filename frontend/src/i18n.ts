// UI translations. French is the reference dictionary: every other language
// must have exactly its keys (the Messages type below makes tsc check it).
// Placeholders like {name} are filled in by translate().

import { createContext, createElement, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";

export const LANGS = ["fr", "en", "pl"] as const;
export type Lang = (typeof LANGS)[number];
export const DEFAULT_LANG: Lang = "fr";

/** Shown in the language selector, in their own language. */
export const LANG_NAMES: Record<Lang, string> = {
  fr: "🇫🇷 Français",
  en: "🇬🇧 English",
  pl: "🇵🇱 Polski",
};

/** Locale used to format dates. */
export const LOCALES: Record<Lang, string> = { fr: "fr-FR", en: "en-GB", pl: "pl-PL" };

const fr = {
  "app.title": "Atelier de jeux Pyxel",
  "lang.label": "Langue",
  "server.error": "Erreur du serveur {status}",
  "chat.connectionLost": "La connexion avec Pix a été coupée.",

  "top.myGames": "📂 Mes jeux",
  "top.saved": "✔ Sauvegardé",
  "top.saving": "Sauvegarde…",
  "top.notSaved": "⚠ Pas sauvegardé",
  "top.exportTitle": "Télécharger le jeu dans un fichier zip",
  "top.export": "📦 Exporter",
  "top.storyTitle": "Le livret de ton jeu, à imprimer ou à garder",
  "top.storyBusy": "Je prépare ton livret…",
  "top.story": "📖 Mon histoire (PDF)",
  "top.storyError": "Oups, impossible de créer le livret : {error}",
  "top.storyFile": "histoire",
  "app.undoConfirm":
    "Annuler ce message ? Le jeu reviendra comme il était juste avant, et la suite de la discussion sera effacée.",
  "app.askFix": "Mon jeu affiche cette erreur, tu peux m'aider à la réparer ?",

  "chat.title": "💬 Discussion",
  "chat.thinking": "🤔 Je réfléchis…",
  "chat.undoTitle": "Remettre le jeu comme avant ce message",
  "chat.undo": "↩️ Annuler",
  "chat.idea1": "Je veux créer un jeu de labyrinthe",
  "chat.idea2": "Un jeu de tir dans l'espace",
  "chat.idea3": "Un chat qui attrape des poissons",
  "chat.error": "Oups, impossible de parler à Pix : {error}",
  "chat.placeholder": "Dis à Pix quoi construire ou changer…",
  "chat.stop": "⏹ Arrêter",
  "chat.send": "Envoyer",

  "right.preview": "🎮 Aperçu",
  "right.code": "📝 Code",
  "right.sprites": "🎨 Sprites",
  "right.run": "▶ Lancer",
  "right.gameFrame": "Jeu Pyxel",
  "right.playHint": "Clique sur le jeu, puis utilise le clavier pour jouer !",
  "right.codeHint":
    "Voici le vrai code de ton jeu. Tu peux le modifier, puis appuyer sur ▶ Lancer. Pix verra tes changements !",
  "right.added": "ajouté",
  "right.changed": "modifié",
  "right.deleted": "effacé (au dernier changement)",
  "right.spritesHint":
    "Dessine ou modifie tes personnages, décors et musiques ici (Pix peut aussi en créer pour toi). Clique sur la 💾 disquette en haut de l'éditeur pour enregistrer, sinon tes changements seront perdus !",
  "right.reloadTitle": "Recharger les dessins et les sons enregistrés (ce qui n'est pas enregistré sera perdu)",
  "right.reload": "🔄 Recharger",
  "right.editorFrame": "Éditeur de sprites Pyxel",
  "right.bug": "🐞 Ton jeu a un bug.",
  "right.askFix": "Demander à Pix de le réparer",

  "picker.title": "🎮 Atelier de jeux Pyxel",
  "picker.newGame": "Nouveau jeu",
  "picker.namePlaceholder": "Le nom de ton jeu (ex : Le labyrinthe du chat)",
  "picker.create": "Créer",
  "picker.myGames": "Mes jeux",
  "picker.importing": "Import en cours…",
  "picker.import": "📥 Importer un jeu",
  "picker.error": "Oups : {error}",
  "picker.loading": "Chargement…",
  "picker.empty": "Pas encore de jeu. Crée le premier !",
  "picker.updated": "modifié le {date}",
  "picker.deleteTitle": "Supprimer ce jeu",
  "picker.deleteLabel": "Supprimer {name}",
  "picker.deleteConfirm": "Supprimer « {name} » ? Le jeu et toute son histoire seront effacés pour toujours.",

  "tool.read": "📖 Je lis ton code…",
  "tool.write": "✍️ J'écris le code…",
  "tool.edit": "✍️ Je modifie le code…",
  "tool.view_resources": "🎨 Je regarde tes dessins et tes sons…",
  "tool.edit_resources": "🎨 Je dessine et je compose…",
  "tool.test_game": "🧪 Je teste le jeu…",
  "tool.default": "🛠️ Je travaille…",
};

export type MessageKey = keyof typeof fr;
/** Exactly the keys of the French dictionary, no more, no less. */
export type Messages = { [K in MessageKey]: string };

const en: Messages = {
  "app.title": "Pyxel Game Workshop",
  "lang.label": "Language",
  "server.error": "Server error {status}",
  "chat.connectionLost": "The connection to Pix was lost.",

  "top.myGames": "📂 My games",
  "top.saved": "✔ Saved",
  "top.saving": "Saving…",
  "top.notSaved": "⚠ Not saved",
  "top.exportTitle": "Download the game as a zip file",
  "top.export": "📦 Export",
  "top.storyTitle": "Your game's booklet, to print or to keep",
  "top.storyBusy": "Making your booklet…",
  "top.story": "📖 My story (PDF)",
  "top.storyError": "Oops, couldn't make the booklet: {error}",
  "top.storyFile": "story",
  "app.undoConfirm":
    "Undo this message? The game will go back to how it was just before, and the rest of the chat will be erased.",
  "app.askFix": "My game shows this error, can you help me fix it?",

  "chat.title": "💬 Chat",
  "chat.thinking": "🤔 Thinking…",
  "chat.undoTitle": "Put the game back to how it was before this message",
  "chat.undo": "↩️ Undo",
  "chat.idea1": "I want to make a maze game",
  "chat.idea2": "A space shooter game",
  "chat.idea3": "A cat that catches fish",
  "chat.error": "Oops, couldn't talk to Pix: {error}",
  "chat.placeholder": "Tell Pix what to build or change…",
  "chat.stop": "⏹ Stop",
  "chat.send": "Send",

  "right.preview": "🎮 Preview",
  "right.code": "📝 Code",
  "right.sprites": "🎨 Sprites",
  "right.run": "▶ Run",
  "right.gameFrame": "Pyxel game",
  "right.playHint": "Click on the game, then use the keyboard to play!",
  "right.codeHint":
    "This is the real code of your game. You can change it, then press ▶ Run. Pix will see your changes!",
  "right.added": "added",
  "right.changed": "changed",
  "right.deleted": "deleted (in the last change)",
  "right.spritesHint":
    "Draw or change your characters, backgrounds and music here (Pix can make some for you too). Click the 💾 floppy disk at the top of the editor to save, or your changes will be lost!",
  "right.reloadTitle": "Reload the saved drawings and sounds (anything not saved will be lost)",
  "right.reload": "🔄 Reload",
  "right.editorFrame": "Pyxel sprite editor",
  "right.bug": "🐞 Your game has a bug.",
  "right.askFix": "Ask Pix to fix it",

  "picker.title": "🎮 Pyxel Game Workshop",
  "picker.newGame": "New game",
  "picker.namePlaceholder": "Your game's name (e.g. The Cat's Maze)",
  "picker.create": "Create",
  "picker.myGames": "My games",
  "picker.importing": "Importing…",
  "picker.import": "📥 Import a game",
  "picker.error": "Oops: {error}",
  "picker.loading": "Loading…",
  "picker.empty": "No games yet. Make the first one!",
  "picker.updated": "changed on {date}",
  "picker.deleteTitle": "Delete this game",
  "picker.deleteLabel": "Delete {name}",
  "picker.deleteConfirm": "Delete “{name}”? The game and its whole story will be erased forever.",

  "tool.read": "📖 Reading your code…",
  "tool.write": "✍️ Writing the code…",
  "tool.edit": "✍️ Changing the code…",
  "tool.view_resources": "🎨 Looking at your drawings and sounds…",
  "tool.edit_resources": "🎨 Drawing and making music…",
  "tool.test_game": "🧪 Testing the game…",
  "tool.default": "🛠️ Working on it…",
};

const pl: Messages = {
  "app.title": "Warsztat gier Pyxel",
  "lang.label": "Język",
  "server.error": "Błąd serwera {status}",
  "chat.connectionLost": "Połączenie z Pixem zostało przerwane.",

  "top.myGames": "📂 Moje gry",
  "top.saved": "✔ Zapisano",
  "top.saving": "Zapisywanie…",
  "top.notSaved": "⚠ Nie zapisano",
  "top.exportTitle": "Pobierz grę jako plik zip",
  "top.export": "📦 Eksportuj",
  "top.storyTitle": "Książeczka o twojej grze, do wydrukowania albo na pamiątkę",
  "top.storyBusy": "Przygotowuję twoją książeczkę…",
  "top.story": "📖 Moja historia (PDF)",
  "top.storyError": "Ups, nie udało się zrobić książeczki: {error}",
  "top.storyFile": "historia",
  "app.undoConfirm":
    "Cofnąć tę wiadomość? Gra wróci do tego, jak wyglądała tuż przed nią, a dalsza część rozmowy zostanie usunięta.",
  "app.askFix": "Moja gra pokazuje ten błąd, pomożesz mi go naprawić?",

  "chat.title": "💬 Rozmowa",
  "chat.thinking": "🤔 Myślę…",
  "chat.undoTitle": "Przywróć grę do stanu sprzed tej wiadomości",
  "chat.undo": "↩️ Cofnij",
  "chat.idea1": "Chcę zrobić grę w labirynt",
  "chat.idea2": "Strzelanka w kosmosie",
  "chat.idea3": "Kot, który łapie ryby",
  "chat.error": "Ups, nie mogę porozmawiać z Pixem: {error}",
  "chat.placeholder": "Powiedz Pixowi, co zbudować albo zmienić…",
  "chat.stop": "⏹ Zatrzymaj",
  "chat.send": "Wyślij",

  "right.preview": "🎮 Podgląd",
  "right.code": "📝 Kod",
  "right.sprites": "🎨 Sprite'y",
  "right.run": "▶ Uruchom",
  "right.gameFrame": "Gra Pyxel",
  "right.playHint": "Kliknij w grę, a potem graj za pomocą klawiatury!",
  "right.codeHint":
    "To jest prawdziwy kod twojej gry. Możesz go zmienić, a potem nacisnąć ▶ Uruchom. Pix zobaczy twoje zmiany!",
  "right.added": "dodane",
  "right.changed": "zmienione",
  "right.deleted": "usunięte (w ostatniej zmianie)",
  "right.spritesHint":
    "Tutaj możesz rysować i zmieniać swoje postacie, tła i muzykę (Pix też może je dla ciebie zrobić). Kliknij 💾 dyskietkę na górze edytora, żeby zapisać, inaczej twoje zmiany przepadną!",
  "right.reloadTitle": "Wczytaj ponownie zapisane rysunki i dźwięki (to, co niezapisane, przepadnie)",
  "right.reload": "🔄 Wczytaj ponownie",
  "right.editorFrame": "Edytor sprite'ów Pyxel",
  "right.bug": "🐞 Twoja gra ma błąd.",
  "right.askFix": "Poproś Pixa o naprawę",

  "picker.title": "🎮 Warsztat gier Pyxel",
  "picker.newGame": "Nowa gra",
  "picker.namePlaceholder": "Nazwa twojej gry (np. Labirynt kota)",
  "picker.create": "Utwórz",
  "picker.myGames": "Moje gry",
  "picker.importing": "Importowanie…",
  "picker.import": "📥 Importuj grę",
  "picker.error": "Ups: {error}",
  "picker.loading": "Ładowanie…",
  "picker.empty": "Nie masz jeszcze żadnej gry. Stwórz pierwszą!",
  "picker.updated": "zmieniono {date}",
  "picker.deleteTitle": "Usuń tę grę",
  "picker.deleteLabel": "Usuń {name}",
  "picker.deleteConfirm": "Usunąć „{name}”? Gra i cała jej historia zostaną usunięte na zawsze.",

  "tool.read": "📖 Czytam twój kod…",
  "tool.write": "✍️ Piszę kod…",
  "tool.edit": "✍️ Zmieniam kod…",
  "tool.view_resources": "🎨 Oglądam twoje rysunki i dźwięki…",
  "tool.edit_resources": "🎨 Rysuję i komponuję…",
  "tool.test_game": "🧪 Testuję grę…",
  "tool.default": "🛠️ Pracuję…",
};

export const MESSAGES: Record<Lang, Messages> = { fr, en, pl };

export const isLang = (v: unknown): v is Lang => typeof v === "string" && (LANGS as readonly string[]).includes(v);

/** The browser's language if we have it (pl*, en*), French otherwise. */
export function detectLang(navLang: string | undefined): Lang {
  const l = (navLang ?? "").toLowerCase();
  if (l.startsWith("pl")) return "pl";
  if (l.startsWith("en")) return "en";
  return "fr";
}

export function translate(lang: Lang, key: MessageKey, vars?: Record<string, string | number>): string {
  const text = MESSAGES[lang][key];
  return vars ? text.replace(/\{(\w+)\}/g, (m, k: string) => (k in vars ? String(vars[k]) : m)) : text;
}

const STORAGE_KEY = "lang";

function storedLang(): Lang | null {
  try {
    const v = typeof localStorage !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null;
    return isLang(v) ? v : null;
  } catch {
    return null;
  }
}

// The current UI language, also read outside React (api.ts sends it as X-Lang).
let current: Lang = storedLang() ?? detectLang(typeof navigator !== "undefined" ? navigator.language : undefined);

export const getLang = (): Lang => current;

export function setLang(lang: Lang): void {
  current = lang;
  try {
    if (typeof localStorage !== "undefined") localStorage.setItem(STORAGE_KEY, lang);
  } catch {
    // Private mode or storage disabled: the choice just won't be remembered.
  }
}

export type T = (key: MessageKey, vars?: Record<string, string | number>) => string;

interface I18n {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: T;
}

const I18nContext = createContext<I18n | null>(null);

export function I18nProvider(props: { children: ReactNode }) {
  const [lang, setState] = useState<Lang>(getLang);
  const change = useCallback((l: Lang) => {
    setLang(l);
    setState(l);
  }, []);
  useEffect(() => {
    document.documentElement.lang = lang;
    document.title = translate(lang, "app.title");
  }, [lang]);
  const value = useMemo<I18n>(
    () => ({ lang, setLang: change, t: (key, vars) => translate(lang, key, vars) }),
    [lang, change],
  );
  return createElement(I18nContext.Provider, { value }, props.children);
}

export function useI18n(): I18n {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used inside <I18nProvider>");
  return ctx;
}
