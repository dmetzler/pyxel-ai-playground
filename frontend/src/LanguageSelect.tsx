import { LANG_NAMES, LANGS, isLang, useI18n } from "./i18n";

export default function LanguageSelect(props: { disabled?: boolean }) {
  const { lang, setLang, t } = useI18n();
  return (
    <select
      className="lang-select"
      aria-label={t("lang.label")}
      title={t("lang.label")}
      value={lang}
      disabled={props.disabled}
      onChange={(e) => {
        if (isLang(e.target.value)) setLang(e.target.value);
      }}
    >
      {LANGS.map((l) => (
        <option key={l} value={l}>
          {LANG_NAMES[l]}
        </option>
      ))}
    </select>
  );
}
