/**
 * i18next initialisation.
 * Language is detected from localStorage first, then browser language.
 * Falls back to English.
 */

import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import de from "./de.json";
import en from "./en.json";

// Read saved language from localStorage
const savedLang = localStorage.getItem("paperless-rag-lang");
const browserLang = navigator.language.startsWith("de") ? "de" : "en";
const initialLang = savedLang || browserLang;

i18n.use(initReactI18next).init({
  resources: {
    de: { translation: de },
    en: { translation: en },
  },
  lng: initialLang,
  fallbackLng: "en",
  interpolation: {
    escapeValue: false,
  },
});

export default i18n;