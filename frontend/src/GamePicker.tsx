import { useEffect, useRef, useState } from "react";
import { GameSummary, deleteGame, importGame, listGames } from "./api";

export default function GamePicker(props: {
  onOpen: (id: string) => void;
  onCreate: (name: string) => Promise<void>;
}) {
  const [games, setGames] = useState<GameSummary[] | null>(null);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const refresh = () => listGames().then(setGames, (e) => setError(String(e.message ?? e)));
  useEffect(() => {
    refresh();
  }, []);

  const report = (e: unknown) => setError(e instanceof Error ? e.message : String(e));

  const create = async () => {
    if (!name.trim()) return;
    try {
      await props.onCreate(name.trim());
    } catch (e) {
      report(e);
    }
  };

  const remove = async (g: GameSummary) => {
    if (!window.confirm(`Supprimer « ${g.name} » ? Le jeu et toute son histoire seront effacés pour toujours.`)) {
      return;
    }
    setError(null);
    try {
      await deleteGame(g.id);
      await refresh();
    } catch (e) {
      report(e);
    }
  };

  const importZip = async (file: File | undefined) => {
    if (!file) return;
    setError(null);
    setImporting(true);
    try {
      const { id } = await importGame(file);
      props.onOpen(id);
    } catch (e) {
      report(e);
      setImporting(false);
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
        <div className="games-head">
          <h2>Mes jeux</h2>
          <button className="import" disabled={importing} onClick={() => fileInput.current?.click()}>
            {importing ? "Import en cours…" : "📥 Importer un jeu"}
          </button>
          <input
            ref={fileInput}
            type="file"
            accept=".zip,application/zip"
            hidden
            onChange={(e) => {
              importZip(e.target.files?.[0]);
              e.target.value = "";
            }}
          />
        </div>
        {error && <div className="error">Oups : {error}</div>}
        {games === null && !error && <p className="hint">Chargement…</p>}
        {games?.length === 0 && <p className="hint">Pas encore de jeu. Crée le premier !</p>}
        <ul className="game-list">
          {games?.map((g) => (
            <li key={g.id}>
              <button className="open" onClick={() => props.onOpen(g.id)}>
                <strong>{g.name}</strong>
                <span>modifié le {new Date(g.updated * 1000).toLocaleString("fr-FR")}</span>
              </button>
              <button className="delete" title="Supprimer ce jeu" aria-label={`Supprimer ${g.name}`} onClick={() => remove(g)}>
                🗑️
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
