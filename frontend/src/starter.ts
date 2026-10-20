// Le jeu affiché avant que l'élève demande quoi que ce soit : un petit
// "bonjour" pour que l'aperçu ne soit jamais vide. pyxel.text n'affiche que
// de l'ASCII, donc pas d'accents dans le texte à l'écran.
export const STARTER_CODE = `import pyxel


class App:
    def __init__(self):
        pyxel.init(160, 120, title="Mon jeu")
        pyxel.run(self.update, self.draw)

    def update(self):
        pass

    def draw(self):
        pyxel.cls(1)
        pyxel.text(40, 50, "Salut, createur !", 7)
        pyxel.text(22, 64, "Dis a Pix quoi construire :)", 10)


App()
`;

export const WELCOME_MESSAGE = `Salut ! Moi c'est **Pix**, ton copain pour créer des jeux. 🎮

On va fabriquer un vrai jeu vidéo ensemble, une petite étape à la fois. Tu me dis ton idée, j'écris le code et je t'explique ce qu'il fait, et tu vois le jeu prendre vie à droite.

Quel genre de jeu veux-tu créer ? Un **labyrinthe**, un **jeu de tir dans l'espace**, un **jeu de saut**... tout ce que tu veux !`;
