/**
 * Language switcher button – toggles between DE and EN.
 * Saves the selected language to localStorage.
 */

import React from "react";
import { useTranslation } from "react-i18next";

const LanguageSwitcher: React.FC = () => {
  const { i18n } = useTranslation();

  const currentLang = i18n.language.startsWith("de") ? "de" : "en";

  const toggle = () => {
    const newLang = currentLang === "de" ? "en" : "de";
    i18n.changeLanguage(newLang);
    localStorage.setItem("paperless-rag-lang", newLang);
  };

  return (
    <button
      onClick={toggle}
      className="flex items-center gap-1 rounded-lg border border-gray-200 px-2 py-1 text-xs font-medium text-gray-600 transition hover:bg-gray-100"
      title="Switch language / Sprache wechseln"
    >
      <span>{currentLang === "de" ? "🇩🇪" : "🇬🇧"}</span>
      <span>{currentLang === "de" ? "DE" : "EN"}</span>
    </button>
  );
};

export default LanguageSwitcher;
