/**
 * Main chat/search page.
 */

import React, { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import Layout from "@/components/Layout";
import StatusBar from "@/components/StatusBar";
import ChatMessage from "@/components/ChatMessage";
import { useChat } from "@/hooks/useChat";
import { getConfig } from "@/api/client";

const ChatPage: React.FC = () => {
  const { t } = useTranslation();
  const { messages, isLoading, sendMessage, clearMessages } = useChat();
  const [input, setInput] = useState("");
  const [model, setModel] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Load model name for display
  useEffect(() => {
    getConfig().then((c) => setModel(c.llm_model)).catch(() => {});
  }, []);

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim() || isLoading) return;
    const query = input.trim();
    setInput("");
    await sendMessage(query);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // Example questions from i18n
  const exampleQuestions = [
    t("chat.examples.q1"),
    t("chat.examples.q2"),
    t("chat.examples.q3"),
  ];

  return (
    <Layout model={model}>
      <StatusBar />

      <div className="mx-auto flex max-w-4xl flex-col" style={{ height: "calc(100vh - 120px)" }}>
        {/* Messages area */}
        <div className="flex-1 overflow-y-auto px-4 py-6">
          {messages.length === 0 ? (
            // Empty state
            <div className="flex h-full flex-col items-center justify-center text-center">
              <span className="text-6xl mb-4">📄</span>
              <h2 className="text-xl font-semibold text-gray-700">
                {t("app.title")}
              </h2>
              <p className="mt-2 text-gray-400 max-w-sm">
                {t("chat.placeholder")}
              </p>

              {/* Example questions */}
              <div className="mt-6 flex flex-col gap-2 w-full max-w-sm">
                {exampleQuestions.map((q) => (
                  <button
                    key={q}
                    onClick={() => sendMessage(q)}
                    className="rounded-xl border border-gray-200 bg-white px-4 py-3 text-left text-sm text-gray-600 shadow-sm transition hover:border-primary-300 hover:bg-primary-50 hover:text-primary-700"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-6">
              {messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input area */}
        <div className="border-t border-gray-200 bg-white px-4 py-4">
          <form onSubmit={handleSubmit} className="flex gap-3 items-end">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={t("chat.placeholder")}
              rows={1}
              className="flex-1 resize-none rounded-xl border border-gray-300 px-4 py-3 text-sm outline-none transition focus:border-primary-400 focus:ring-2 focus:ring-primary-100"
              style={{ maxHeight: "120px" }}
              disabled={isLoading}
            />

            {/* Clear button */}
            {messages.length > 0 && (
              <button
                type="button"
                onClick={clearMessages}
                className="rounded-xl border border-gray-300 p-3 text-gray-400 transition hover:bg-gray-50 hover:text-gray-600"
                title={t("chat.clearHistory")}
              >
                🗑️
              </button>
            )}

            {/* Send button */}
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="rounded-xl bg-primary-600 px-4 py-3 text-white transition hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <svg className="h-5 w-5 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
              ) : (
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              )}
            </button>
          </form>

          <p className="mt-2 text-center text-xs text-gray-400">
            {t("chat.newLine")}
          </p>
        </div>
      </div>
    </Layout>
  );
};

export default ChatPage;