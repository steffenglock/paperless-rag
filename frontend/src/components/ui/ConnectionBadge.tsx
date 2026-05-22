/**
 * Green/red connection status badge.
 */

import React from "react";
import { useTranslation } from "react-i18next";
import type { ConnectionStatus } from "@/types";

interface ConnectionBadgeProps {
  status: ConnectionStatus;
  message?: string;
}

const ConnectionBadge: React.FC<ConnectionBadgeProps> = ({ status, message }) => {
  const { t } = useTranslation();

  if (status === "idle") return null;

  const styles: Record<string, string> = {
    testing: "bg-yellow-100 text-yellow-800 border-yellow-300",
    success: "bg-green-100 text-green-800 border-green-300",
    error: "bg-red-100 text-red-800 border-red-300",
  };

  const icons: Record<string, string> = {
    testing: "⏳",
    success: "✅",
    error: "❌",
  };

  return (
    <div
      className={`mt-2 rounded-lg border px-3 py-2 text-sm ${styles[status]}`}
    >
      {icons[status]} {message || (status === "success" ? t("settings.connected") : t("errors.connectionFailed"))}
    </div>
  );
};

export default ConnectionBadge;
