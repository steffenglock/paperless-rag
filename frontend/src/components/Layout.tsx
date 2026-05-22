/**
 * Main application layout with top navigation bar.
 */

import React from "react";
import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import LanguageSwitcher from "./LanguageSwitcher";

interface LayoutProps {
  children: React.ReactNode;
  model?: string;
}

const Layout: React.FC<LayoutProps> = ({ children, model }) => {
  const { t } = useTranslation();
  const location = useLocation();

  return (
    <div className="flex min-h-screen flex-col bg-gray-50">
      {/* Top navigation */}
      <header className="border-b border-gray-200 bg-white shadow-sm">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-3">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2">
            <span className="text-2xl">📄</span>
            <span className="font-bold text-primary-700">{t("app.title")}</span>
          </Link>

          {/* Right side controls */}
          <div className="flex items-center gap-3">
            {/* Model display */}
            {model && (
              <span className="hidden rounded-full bg-primary-50 px-3 py-1 text-xs font-medium text-primary-700 sm:block">
                {t("status.model", { model })}
              </span>
            )}

            {/* Language switcher */}
            <LanguageSwitcher />

            {/* Settings icon */}
            <Link
              to="/settings"
              className={`rounded-lg p-2 transition hover:bg-gray-100 ${
                location.pathname === "/settings"
                  ? "text-primary-600"
                  : "text-gray-500"
              }`}
              title={t("nav.settings")}
            >
              <svg
                className="h-5 w-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                />
              </svg>
            </Link>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1">{children}</main>
    </div>
  );
};

export default Layout;