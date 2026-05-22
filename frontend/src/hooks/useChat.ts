/**
 * Custom hook managing chat state and RAG search logic.
 * Supports both regular and streaming responses.
 */

import { useState, useCallback } from "react";
import { ragSearch } from "@/api/client";
import type { Message } from "@/components/ChatMessage";

let messageIdCounter = 0;
const newId = () => `msg-${++messageIdCounter}`;

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = useCallback(async (query: string) => {
    if (!query.trim() || isLoading) return;

    // Add user message
    const userMsg: Message = {
      id: newId(),
      role: "user",
      content: query,
    };

    // Add placeholder assistant message
    const assistantId = newId();
    const assistantMsg: Message = {
      id: assistantId,
      role: "assistant",
      content: "",
      isStreaming: true,
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setIsLoading(true);

    try {
      const result = await ragSearch(query);

      // Replace placeholder with real answer
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? {
                ...m,
                content: result.answer,
                sources: result.sources,
                isStreaming: false,
              }
            : m
        )
      );
    } catch (error: any) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? {
                ...m,
                content: `❌ Fehler: ${error.message}`,
                isStreaming: false,
              }
            : m
        )
      );
    } finally {
      setIsLoading(false);
    }
  }, [isLoading]);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  return { messages, isLoading, sendMessage, clearMessages };
}
