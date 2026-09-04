"use client";

import { useI18n } from "@/lib/i18n";

export function LanguageSwitcher() {
  const { lang, setLang } = useI18n();

  return (
    <div className="lang-switcher" role="group" aria-label="Language selection">
      <button
        type="button"
        className={`lang-btn ${lang === "ko" ? "active" : ""}`}
        onClick={() => setLang("ko")}
        aria-pressed={lang === "ko"}
      >
        한국어
      </button>
      <span className="lang-divider">|</span>
      <button
        type="button"
        className={`lang-btn ${lang === "en" ? "active" : ""}`}
        onClick={() => setLang("en")}
        aria-pressed={lang === "en"}
      >
        English
      </button>
    </div>
  );
}
