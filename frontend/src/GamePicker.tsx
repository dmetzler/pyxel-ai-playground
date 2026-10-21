import { useEffect, useRef, useState } from "react";
import { GameSummary, deleteGame, importGame, listGames } from "./api";
import { LOCALES, useI18n } from "./i18n";
import LanguageSelect from "./LanguageSelect";

export default function GamePicker(props: {
  onOpen: (id: string) => void;
  onCreate: (name: string) => Promise<void>;
}) {
  const { lang, t } = useI18n();
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
    if (!window.confirm(t("picker.deleteConfirm", { name: g.name }))) {
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
        <div className="picker-head">
          <h1>{t("picker.title")}</h1>
          <LanguageSelect />
        </div>
        <h2>{t("picker.newGame")}</h2>
        <form
          className="new-game"
          onSubmit={(e) => {
            e.preventDefault();
            create();
          }}
        >
          <input
            value={name}
            placeholder={t("picker.namePlaceholder")}
            onChange={(e) => setName(e.target.value)}
            autoFocus
          />
          <button type="submit" disabled={!name.trim()}>{t("picker.create")}</button>
        </form>
        <div className="games-head">
          <h2>{t("picker.myGames")}</h2>
          <button className="import" disabled={importing} onClick={() => fileInput.current?.click()}>
            {importing ? t("picker.importing") : t("picker.import")}
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
        {error && <div className="error">{t("picker.error", { error })}</div>}
        {games === null && !error && <p className="hint">{t("picker.loading")}</p>}
        {games?.length === 0 && <p className="hint">{t("picker.empty")}</p>}
        <ul className="game-list">
          {games?.map((g) => (
            <li key={g.id}>
              <button className="open" onClick={() => props.onOpen(g.id)}>
                <strong>{g.name}</strong>
                <span>{t("picker.updated", { date: new Date(g.updated * 1000).toLocaleString(LOCALES[lang]) })}</span>
              </button>
              <button className="delete" title={t("picker.deleteTitle")} aria-label={t("picker.deleteLabel", { name: g.name })} onClick={() => remove(g)}>
                🗑️
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
