/**
 * Root application component with routing.
 * Shows the Setup wizard if the app is not yet configured.
 */

import React, { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import "./i18n";
import SetupWizard from "@/pages/Setup";
import { getConfig } from "@/api/client";

// Lazy placeholders for pages built in later steps
const ChatPage = React.lazy(() => import("@/pages/Chat"));
const SettingsPage = React.lazy(() => import("@/pages/Settings"));

type AppState = "loading" | "setup" | "ready";

const AppRoutes: React.FC<{ appState: AppState; onSetupDone: () => void }> = ({
  appState,
  onSetupDone,
}) => {
  if (appState === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="mx-auto h-10 w-10 animate-spin rounded-full border-4 border-primary-600 border-t-transparent" />
          <p className="mt-4 text-gray-500">Paperless RAG …</p>
        </div>
      </div>
    );
  }

  if (appState === "setup") {
    return <SetupWizard onDone={onSetupDone} />;
  }

  return (
    <React.Suspense
      fallback={
        <div className="p-8 text-center text-gray-500">Loading …</div>
      }
    >
      <Routes>
        <Route path="/" element={<ChatPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </React.Suspense>
  );
};

const App: React.FC = () => {
  const [appState, setAppState] = useState<AppState>("loading");

  useEffect(() => {
    getConfig()
      .then((config) => {
        const isConfigured =
          config.paperless_url.trim() !== "" &&
          config.llm_model.trim() !== "";
        setAppState(isConfigured ? "ready" : "setup");
      })
      .catch(() => setAppState("setup"));
  }, []);

  return (
    <BrowserRouter>
      <AppRoutes
        appState={appState}
        onSetupDone={() => setAppState("ready")}
      />
    </BrowserRouter>
  );
};

export default App;