"""Backend strings in French, English and Polish.

A game has its own language (meta.json "lang"): it picks Pix's prompt, the git
commit messages and the story PDF. Error details sent back to the UI follow the
X-Lang header of the request instead (the language the kid sees right now).
"""
import contextvars
import datetime

LANGS = ("fr", "en", "pl")
DEFAULT_LANG = "fr"

# Language of the current HTTP request (X-Lang header), set by LangMiddleware.
request_lang: contextvars.ContextVar[str] = contextvars.ContextVar("request_lang", default=DEFAULT_LANG)


def norm_lang(value) -> str:
    """`value` if it is a supported language, else the default ("fr")."""
    return value if isinstance(value, str) and value in LANGS else DEFAULT_LANG


STRINGS: dict[str, dict[str, str]] = {
    "fr": {
        # git commit messages
        "commit_student": "Modifications de l'élève",
        "commit_pix": "Pix : {msg}",
        "commit_start": "Début du jeu",
        "commit_undo": "Annulation : retour à la version {commit}",
        # error details (HTTPException) and the chat error
        "game_not_found": "Jeu introuvable",
        "pix_busy": "Pix est encore en train de travailler.",
        "pix_busy_game": "Pix travaille encore sur ce jeu.",
        "unknown_version": "Version inconnue",
        "zip_too_big": "Ce fichier est trop gros.",
        "zip_bad_paths": "Ce fichier zip contient des chemins interdits.",
        "zip_no_game": "Ce fichier zip ne contient pas de jeu (game.py manquant).",
        "zip_unreadable": "Ce fichier n'est pas un jeu exporté (zip illisible).",
        "pix_problem": "Pix a eu un problème : {error}",
        # default game names
        "default_name": "Mon jeu",
        "imported_name": "Jeu importé",
        # appended to Pix's prompt
        "agent_files": "\n\n## Les fichiers de CE jeu\n- Le code : `{code}`\n"
                       "- Les ressources : `{res}` (avec les outils `view_resources` et `edit_resources`)\n",
        # story PDF
        "story_file": "histoire",
        "story_page": "page",
        "story_noshot": "Pas d'image pour cette étape : le jeu ne démarrait pas encore.",
        "story_legend": "nouveau ou modifié",
        "story_no_answer": "Pix n'a pas eu le temps de répondre à cette étape.",
        "story_kicker": "Mon carnet de création de jeu",
        "story_app_caption": "L'atelier : à gauche, je discute avec Pix, mon assistant ; à droite, "
                             "je vois mon jeu, son code et ses dessins.",
        "story_final_caption": "Mon jeu à la fin de la séance.",
        "story_chapter_steps": "Ce que nous avons fait",
        "story_no_steps": "Ce jeu n'a pas encore d'histoire : demande quelque chose à Pix "
                          "et chaque étape apparaîtra ici, avec le code qui a changé.",
        "story_intro_steps": "Le jeu a été construit en {n} {steps}. À chaque fois, tu as demandé quelque chose "
                             "à Pix, il a modifié le programme et t'a expliqué ce qu'il faisait. Les lignes "
                             "<b>surlignées en vert</b> sont celles qui ont été ajoutées ou changées.",
        "story_step_one": "étape",
        "story_step_many": "étapes",
        "story_step": "Étape {n}",
        "story_you_asked": "Tu as demandé",
        "story_pix_explained": "Pix t'a expliqué",
        "story_after_step": "Le jeu après l'étape {n}.",
        "story_step_code": "Le code de cette étape",
        "story_no_change": "Pas de changement dans le code à cette étape.",
        "story_chapter_code": "Le code complet de ton jeu",
        "story_code_intro": "Voici tout le programme <b>game.py</b> ({lines} lignes). "
                            "Tu peux le recopier ou le retrouver dans le fichier exporté.",
        "story_chapter_home": "Pour continuer à la maison",
        "story_home_install": "Installe Python (sur <b>python.org</b>), puis Pyxel en tapant dans un terminal :",
        "story_home_file": "Mets ton programme dans un fichier <b>game.py</b>",
        "story_home_res": " et le fichier de dessins et de sons <b>res.pyxres</b> dans le même dossier",
        "story_home_export": ". Le bouton <b>Exporter</b> de l'atelier te donne tout dans un fichier zip.",
        "story_home_run": "Lance ton jeu :",
        "story_home_edit": "Pour modifier les dessins et les sons :",
        "story_tip_title": "Quelques idées pour aller plus loin :",
        "story_tip_1": "Change une couleur ou une vitesse, relance le jeu et regarde ce qui se passe.",
        "story_tip_2": "Ajoute un écran « Partie terminée » avec ton score.",
        "story_tip_3": "Rends le jeu de plus en plus difficile au fil du temps.",
        "story_tip_end": "Le plus important : essaie, casse, répare. C'est comme ça qu'on apprend à programmer !",
    },
    "en": {
        "commit_student": "Student's changes",
        "commit_pix": "Pix: {msg}",
        "commit_start": "Start of the game",
        "commit_undo": "Undo: back to version {commit}",
        "game_not_found": "Game not found",
        "pix_busy": "Pix is still working.",
        "pix_busy_game": "Pix is still working on this game.",
        "unknown_version": "Unknown version",
        "zip_too_big": "This file is too big.",
        "zip_bad_paths": "This zip file contains forbidden paths.",
        "zip_no_game": "This zip file does not contain a game (game.py is missing).",
        "zip_unreadable": "This file is not an exported game (unreadable zip).",
        "pix_problem": "Pix ran into a problem: {error}",
        "default_name": "My game",
        "imported_name": "Imported game",
        "agent_files": "\n\n## The files of THIS game\n- The code: `{code}`\n"
                       "- The resources: `{res}` (with the tools `view_resources` and `edit_resources`)\n",
        "story_file": "story",
        "story_page": "page",
        "story_noshot": "No picture for this step: the game did not start yet.",
        "story_legend": "new or changed",
        "story_no_answer": "Pix did not have time to answer at this step.",
        "story_kicker": "My game-making notebook",
        "story_app_caption": "The workshop: on the left, I chat with Pix, my assistant; on the right, "
                             "I see my game, its code and its drawings.",
        "story_final_caption": "My game at the end of the session.",
        "story_chapter_steps": "What we did",
        "story_no_steps": "This game has no story yet: ask Pix for something "
                          "and each step will show up here, with the code that changed.",
        "story_intro_steps": "The game was built in {n} {steps}. Each time, you asked Pix for something, "
                             "he changed the program and explained what he was doing. The lines "
                             "<b>highlighted in green</b> are the ones that were added or changed.",
        "story_step_one": "step",
        "story_step_many": "steps",
        "story_step": "Step {n}",
        "story_you_asked": "You asked",
        "story_pix_explained": "Pix explained",
        "story_after_step": "The game after step {n}.",
        "story_step_code": "The code of this step",
        "story_no_change": "No change to the code at this step.",
        "story_chapter_code": "The full code of your game",
        "story_code_intro": "Here is the whole <b>game.py</b> program ({lines} lines). "
                            "You can copy it or find it in the exported file.",
        "story_chapter_home": "Keep going at home",
        "story_home_install": "Install Python (from <b>python.org</b>), then Pyxel by typing in a terminal:",
        "story_home_file": "Put your program in a file named <b>game.py</b>",
        "story_home_res": " and the drawings and sounds file <b>res.pyxres</b> in the same folder",
        "story_home_export": ". The <b>Export</b> button in the workshop gives you everything in a zip file.",
        "story_home_run": "Run your game:",
        "story_home_edit": "To change the drawings and sounds:",
        "story_tip_title": "A few ideas to go further:",
        "story_tip_1": "Change a colour or a speed, run the game again and see what happens.",
        "story_tip_2": "Add a “Game over” screen with your score.",
        "story_tip_3": "Make the game harder and harder as time goes by.",
        "story_tip_end": "Most important: try, break, fix. That's how you learn to program!",
    },
    "pl": {
        "commit_student": "Zmiany ucznia",
        "commit_pix": "Pix: {msg}",
        "commit_start": "Początek gry",
        "commit_undo": "Cofnięcie: powrót do wersji {commit}",
        "game_not_found": "Nie znaleziono gry",
        "pix_busy": "Pix wciąż pracuje.",
        "pix_busy_game": "Pix wciąż pracuje nad tą grą.",
        "unknown_version": "Nieznana wersja",
        "zip_too_big": "Ten plik jest za duży.",
        "zip_bad_paths": "Ten plik zip zawiera niedozwolone ścieżki.",
        "zip_no_game": "Ten plik zip nie zawiera gry (brak pliku game.py).",
        "zip_unreadable": "Ten plik nie jest wyeksportowaną grą (nieczytelny zip).",
        "pix_problem": "Pix napotkał problem: {error}",
        "default_name": "Moja gra",
        "imported_name": "Zaimportowana gra",
        "agent_files": "\n\n## Pliki TEJ gry\n- Kod: `{code}`\n"
                       "- Zasoby: `{res}` (z narzędziami `view_resources` i `edit_resources`)\n",
        "story_file": "historia",
        "story_page": "strona",
        "story_noshot": "Brak obrazka dla tego kroku: gra jeszcze się nie uruchamiała.",
        "story_legend": "nowe lub zmienione",
        "story_no_answer": "Pix nie zdążył odpowiedzieć w tym kroku.",
        "story_kicker": "Mój dziennik tworzenia gry",
        "story_app_caption": "Pracownia: po lewej rozmawiam z Pixem, moim asystentem; po prawej "
                             "widzę moją grę, jej kod i rysunki.",
        "story_final_caption": "Moja gra na koniec zajęć.",
        "story_chapter_steps": "Co zrobiliśmy",
        "story_no_steps": "Ta gra nie ma jeszcze historii: poproś o coś Pixa, "
                          "a każdy krok pojawi się tutaj, razem z kodem, który się zmienił.",
        "story_intro_steps": "Gra powstała w {n} {steps}. Za każdym razem prosiłeś Pixa o coś, "
                             "a on zmieniał program i wyjaśniał, co robi. Linie "
                             "<b>podświetlone na zielono</b> to te, które zostały dodane lub zmienione.",
        "story_step_one": "kroku",
        "story_step_many": "krokach",
        "story_step": "Krok {n}",
        "story_you_asked": "Twoja prośba",
        "story_pix_explained": "Pix wyjaśnił",
        "story_after_step": "Gra po kroku {n}.",
        "story_step_code": "Kod tego kroku",
        "story_no_change": "Brak zmian w kodzie w tym kroku.",
        "story_chapter_code": "Pełny kod twojej gry",
        "story_code_intro": "Oto cały program <b>game.py</b> (liczba linii: {lines}). "
                            "Możesz go przepisać albo znaleźć w wyeksportowanym pliku.",
        "story_chapter_home": "Graj dalej w domu",
        "story_home_install": "Zainstaluj Pythona (ze strony <b>python.org</b>), a potem Pyxel, "
                              "wpisując w terminalu:",
        "story_home_file": "Zapisz swój program w pliku <b>game.py</b>",
        "story_home_res": ", a plik z rysunkami i dźwiękami <b>res.pyxres</b> w tym samym folderze",
        "story_home_export": ". Przycisk <b>Eksportuj</b> w pracowni daje ci wszystko w pliku zip.",
        "story_home_run": "Uruchom swoją grę:",
        "story_home_edit": "Aby zmienić rysunki i dźwięki:",
        "story_tip_title": "Kilka pomysłów, jak pójść dalej:",
        "story_tip_1": "Zmień kolor albo prędkość, uruchom grę ponownie i zobacz, co się stanie.",
        "story_tip_2": "Dodaj ekran „Koniec gry” z twoim wynikiem.",
        "story_tip_3": "Spraw, żeby gra z czasem robiła się coraz trudniejsza.",
        "story_tip_end": "Najważniejsze: próbuj, psuj, naprawiaj. Tak właśnie uczy się programowania!",
    },
}

MONTHS = {
    "fr": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
           "août", "septembre", "octobre", "novembre", "décembre"],
    "en": ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"],
    # Genitive: "21 października 2026".
    "pl": ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca",
           "sierpnia", "września", "października", "listopada", "grudnia"],
}


def t(lang: str, key: str, **kwargs) -> str:
    """The string `key` in `lang` (French if the language is unknown), formatted with kwargs."""
    s = STRINGS[norm_lang(lang)][key]
    return s.format(**kwargs) if kwargs else s


def tr(key: str, **kwargs) -> str:
    """The string `key` in the current request's language (X-Lang header)."""
    return t(request_lang.get(), key, **kwargs)


def format_date(lang: str, d: datetime.date) -> str:
    lang = norm_lang(lang)
    month = MONTHS[lang][d.month - 1]
    if lang == "en":
        return f"{month} {d.day}, {d.year}"
    day = "1er" if lang == "fr" and d.day == 1 else str(d.day)
    return f"{day} {month} {d.year}"


class LangMiddleware:
    """ASGI middleware: reads X-Lang into `request_lang` for the whole request (streams included)."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        raw = dict(scope.get("headers") or []).get(b"x-lang", b"").decode("latin-1").strip().lower()
        token = request_lang.set(norm_lang(raw))
        try:
            await self.app(scope, receive, send)
        finally:
            request_lang.reset(token)
