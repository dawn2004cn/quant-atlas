import { useTranslation } from "react-i18next";

const LANGUAGES = [
  { code: "zh", label: "中文" },
  { code: "en", label: "English" },
];

export function LanguageSwitcher() {
  const { i18n } = useTranslation();
  const current = i18n.language?.startsWith("zh") ? "zh" : "en";

  return (
    <div className="flex gap-1 text-xs">
      {LANGUAGES.map((lang) => (
        <button
          key={lang.code}
          className={`px-2 py-0.5 rounded ${
            current === lang.code
              ? "bg-purple-100 text-purple-700 font-semibold"
              : "text-slate-500 hover:text-slate-700"
          }`}
          onClick={() => i18n.changeLanguage(lang.code)}
        >
          {lang.label}
        </button>
      ))}
    </div>
  );
}