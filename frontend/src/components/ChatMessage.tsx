/**
 * Single chat message bubble (user or assistant).
 */

import React from "react";
import { useTranslation } from "react-i18next";
import SourceCard from "./SourceCard";
import type { SearchSource } from "@/api/client";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SearchSource[];
  isStreaming?: boolean;
}

interface Props {
  message: Message;
}

const ChatMessage: React.FC<Props> = ({ message }) => {
  const { t } = useTranslation();
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[85%] ${isUser ? "order-2" : "order-1"}`}>
        {/* Avatar */}
        <div
          className={`mb-1 flex items-center gap-1 text-xs text-gray-400 ${
            isUser ? "justify-end" : "justify-start"
          }`}
        >
          <span>{isUser ? "👤" : "🤖"}</span>
        </div>

        {/* Bubble */}
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
            isUser
              ? "bg-primary-600 text-white rounded-tr-sm"
              : "bg-white border border-gray-200 text-gray-800 rounded-tl-sm shadow-sm"
          }`}
        >
          {message.isStreaming && !message.content ? (
            <span className="flex items-center gap-1 text-gray-400">
              <span className="animate-pulse">●</span>
              <span className="animate-pulse delay-100">●</span>
              <span className="animate-pulse delay-200">●</span>
            </span>
          ) : (
            <p className="whitespace-pre-wrap">{message.content}</p>
          )}
        </div>

        {/* Sources */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="mt-2 flex flex-col gap-2">
            <p className="text-xs font-medium text-gray-500 px-1">
              {t("chat.sources")}:
            </p>
            {message.sources.map((source, i) => (
              <SourceCard key={source.document_id} source={source} index={i + 1} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatMessage;
