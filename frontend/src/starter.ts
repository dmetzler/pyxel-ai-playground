// Le jeu affiché avant que l'élève demande quoi que ce soit : un petit
// "bonjour" pour que l'aperçu ne soit jamais vide. pyxel.text n'affiche que
// de l'ASCII, donc pas d'accents dans le texte à l'écran. One version per
// language: a new game starts in the language of the UI.
import { Lang } from "./i18n";

const starter = (title: string, line1: [number, string], line2: [number, string]) => `import pyxel


class App:
    def __init__(self):
        pyxel.init(160, 120, title="${title}")
        pyxel.run(self.update, self.draw)

    def update(self):
        pass

    def draw(self):
        pyxel.cls(1)
        pyxel.text(${line1[0]}, 50, "${line1[1]}", 7)
        pyxel.text(${line2[0]}, 64, "${line2[1]}", 10)


App()
`;

export const STARTER_CODES: Record<Lang, string> = {
  fr: starter("Mon jeu", [40, "Salut, createur !"], [22, "Dis a Pix quoi construire :)"]),
  en: starter("My game", [50, "Hi, game maker!"], [30, "Tell Pix what to build :)"]),
  pl: starter("Moja gra", [52, "Czesc, tworco!"], [20, "Powiedz Pixowi, co zbudowac :)"]),
};

export const WELCOME_MESSAGES: Record<Lang, string> = {
  fr: `Salut ! Moi c'est **Pix**, ton copain pour créer des jeux. 🎮

On va fabriquer un vrai jeu vidéo ensemble, une petite étape à la fois. Tu me dis ton idée, j'écris le code et je t'explique ce qu'il fait, et tu vois le jeu prendre vie à droite.

Quel genre de jeu veux-tu créer ? Un **labyrinthe**, un **jeu de tir dans l'espace**, un **jeu de saut**... tout ce que tu veux !`,
  en: `Hi! I'm **Pix**, your game-making buddy. 🎮

We're going to build a real video game together, one small step at a time. You tell me your idea, I write the code and explain what it does, and you watch the game come to life on the right.

What kind of game do you want to make? A **maze**, a **space shooter**, a **jumping game**... anything you like!`,
  pl: `Cześć! Jestem **Pix**, twój kumpel do tworzenia gier. 🎮

Razem zrobimy prawdziwą grę wideo, krok po kroku. Ty mówisz mi swój pomysł, ja piszę kod i tłumaczę, co robi, a ty patrzysz, jak gra ożywa po prawej stronie.

Jaką grę chcesz stworzyć? **Labirynt**, **strzelankę w kosmosie**, **grę ze skakaniem**... co tylko chcesz!`,
};
