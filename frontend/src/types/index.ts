/**
 * Shared TypeScript types used across the application.
 */

export type Provider = "ollama" | "openai" | "openrouter";

export interface SetupState {
  paperless_url: string;
  paperless_token: string;
  embedding_provider: Provider;
  embedding_base_url: string;
  embedding_api_key: string;
  embedding_model: string;
  llm_provider: Provider;
  llm_base_url: string;
  llm_api_key: string;
  llm_model: string;
}

export type ConnectionStatus = "idle" | "testing" | "success" | "error";
