import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import SourceCard from "./SourceCard";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: any[];
  isStreaming?: boolean;
}

interface Props {
  message: Message;
  paperlessUrl?: string;
}

const ChatMessage: React.FC<Props> = ({ message, paperlessUrl }) => {
  const { t } = useTranslation();
  const isUser = message.role === "user";
  
  // Neuer State für das Akkordeon: Standardmäßig eingeklappt (false)
  const [showSources, setShowSources] = useState(false);

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[85%] ${isUser ? "order-2" : "order-1"}`}>
        <div className={`mb-1 flex items-center gap-1 text-xs text-gray-400 ${isUser ? "justify-end" : "justify-start"}`}>
          <span>{isUser ? "👤" : "🤖"}</span>
        </div>
        <div className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${isUser ? "bg-primary-600 text-white rounded-tr-sm" : "bg-white border border-gray-200 text-gray-800 rounded-tl-sm shadow-sm"}`}>
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
        
        {/* Neue Akkordeon-Logik für die Quellen */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="mt-2 flex flex-col gap-2">
            <button
              onClick={() => setShowSources(!showSources)}
              className="flex items-center gap-1.5 text-xs font-medium text-gray-500 hover:text-gray-700 px-1 transition-colors w-fit cursor-pointer"
            >
              <span className={`transform transition-transform duration-200 ${showSources ? "rotate-90" : "rotate-0"}`}>
                ▶
              </span>
              {showSources 
                ? t("chat.hideSources", "Quellen ausblenden") 
                : `${message.sources.length} ${t("chat.showSources", "Quellen anzeigen")}`}
            </button>

            {/* Die Liste wird nur gerendert, wenn showSources "true" ist */}
            {showSources && (
              <div className="flex flex-col gap-2 mt-1 animate-in fade-in slide-in-from-top-2 duration-200">
                {message.sources.map((source: any, i: number) => (
                  <SourceCard key={i} source={source} index={i + 1} paperlessUrl={paperlessUrl} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatMessage;
