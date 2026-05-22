/**
 * Displays a single source document reference below a chat answer.
 */

import React, { useState } from "react";
import type { SearchSource } from "@/api/client";

interface Props {
  source: SearchSource;
  index: number;
  paperlessUrl?: string;
}

// Kugelsichere Hilfsfunktion zum Entfernen von Slashes am Ende eines Strings
const removeTrailingSlash = (url: any): string => {
  if (!url || typeof url !== "string") return "";
  return url.endsWith("/") ? url.slice(0, -1) : url;
};

const SourceCard: React.FC<Props> = ({ source, index, paperlessUrl }) => {
  const [expanded, setExpanded] = useState(false);

  // Relevance: distance 0 = perfect, 1 = unrelated
  const relevance = Math.round((1 - source.distance) * 100);

  // Konstruiere den direkten Link zum Dokument in Paperless-ngx
  const cleanUrl = removeTrailingSlash(paperlessUrl);
  const docLink = cleanUrl && source.document_id
    ? `${cleanUrl}/documents/${source.document_id}`
    : null;

  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <span className="flex-shrink-0 flex h-5 w-5 items-center justify-center rounded-full bg-primary-100 text-xs font-bold text-primary-700">
            {index}
          </span>
          {docLink ? (
            <a 
              href={docLink}
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-primary-600 hover:text-primary-800 hover:underline truncate"
              title="In Paperless-ngx öffnen"
            >
              {source.document_title || `Dokument #${source.document_id}`}
            </a>
          ) : (
            <span className="font-medium text-gray-700 truncate">
              {source.document_title || `Dokument #${source.document_id}`}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <span
            className={`rounded-full px-2 py-0.5 text-xs font-medium ${
              relevance >= 80
                ? "bg-green-100 text-green-700"
                : relevance >= 60
                ? "bg-yellow-100 text-yellow-700"
                : "bg-gray-100 text-gray-600"
            }`}
          >
            {relevance}%
          </span>
          <button
            onClick={() => setExpanded((e) => !e)}
            className="text-gray-400 hover:text-gray-600 transition"
          >
            {expanded ? "▲" : "▼"}
          </button>
        </div>
      </div>

      {expanded && (
        <p className="mt-2 text-xs text-gray-600 leading-relaxed border-t border-gray-200 pt-2">
          {source.text}
        </p>
      )}
    </div>
  );
};

export default SourceCard;
