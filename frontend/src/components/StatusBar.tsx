/**
 * Status bar showing index stats and connection status.
 */

import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { getIndexStats, getPaperlessStatus } from "@/api/client";

const StatusBar: React.FC = () => {
  const { t } = useTranslation();
  const [docCount, setDocCount] = useState<number | null>(null);
  const [chunkCount, setChunkCount] = useState<number | null>(null);
  const [connected, setConnected] = useState<boolean | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [stats, status] = await Promise.all([
          getIndexStats(),
          getPaperlessStatus(),
        ]);
        setDocCount(stats.indexed_document_count);
        setChunkCount(stats.total_chunks);
        setConnected(status.connected);
      } catch {
        setConnected(false);
      }
    };
    load();
  }, []);

  return (
    <div className="border-b border-gray-100 bg-white px-4 py-2">
      <div className="mx-auto flex max-w-4xl items-center gap-4 text-xs text-gray-500">
        {/* Connection status */}
        <span className="flex items-center gap-1">
          <span
            className={`h-2 w-2 rounded-full ${
              connected === null
                ? "bg-gray-300"
                : connected
                ? "bg-green-500"
                : "bg-red-500"
            }`}
          />
          {connected === null
            ? "…"
            : connected
            ? t("settings.connected")
            : t("settings.disconnected")}
        </span>

        {/* Divider */}
        <span className="text-gray-200">|</span>

        {/* Document count */}
        {docCount !== null && (
          <span>
            {t("status.indexed", { count: docCount })}
          </span>
        )}

        {/* Chunk count */}
        {chunkCount !== null && (
          <span>{t("status.chunks", { count: chunkCount })}</span>
        )}
      </div>
    </div>
  );
};

export default StatusBar;
