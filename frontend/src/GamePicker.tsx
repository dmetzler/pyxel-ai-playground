import { useEffect, useState } from "react";
import { GameSummary, listGames } from "./api";

export default function GamePicker(props: {
  onOpen: (id: string) => void;
  onCreate: (name: string) => Promise<void>;
}) {
  const [games, setGames] = useState<GameSummary[] | null>(null);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listGames().then(setGames, (e) => setError(String(e.message ?? e)));
  }, []);

  const create = async () => {
    if (!name.trim()) return;
    try {
      await props.onCreate(name.trim());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <div className="picker">
      <div className="pane picker-card">
        <h1>🎮 Atelier de jeux Pyxel</h1>
        <h2>Nouveau jeu</h2>
        <form
          className="new-game"
          onSubmit={(e) => {
            e.preventDefault();
            create();
          }}
        >
          <input
            value={name}
            placeholder="Le nom de ton jeu (ex : Le labyrinthe du chat)"
            onChange={(e) => setName(e.target.value)}
            autoFocus
          />
          <button type="submit" disabled={!name.trim()}>Créer</button>
        </form>
        <h2>Mes jeux</h2>
        {error && <div className="error">Oups : {error}</div>}
        {games === null && !error && <p className="hint">Chargement…</p>}
        {games?.length === 0 && <p className="hint">Pas encore de jeu. Crée le premier !</p>}
        <ul className="game-list">
          {games?.map((g) => (
            <li key={g.id}>
              <button onClick={() => props.onOpen(g.id)}>
                <strong>{g.name}</strong>
                <span>modifié le {new Date(g.updated * 1000).toLocaleString("fr-FR")}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
