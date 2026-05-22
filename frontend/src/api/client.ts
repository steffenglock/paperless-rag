/**
 * Central API client.
 * All backend calls go through these functions.
 */

const API_BASE = "/api";

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

/**
 * Remove masked values (containing •) from a config object before saving.
 * This prevents sending partially masked tokens back to the backend.
 */
export function stripMasked(data: Partial<AppConfig>): Partial<AppConfig> {
  const result: Partial<AppConfig> = {};
  for (const [key, value] of Object.entries(data)) {
    if (typeof value === "string" && value.includes("•")) {
      // Skip masked values – keep existing value in DB
      continue;
    }
    (result as any)[key] = value;
  }
  return result;
}

// ── Config ────────────────────────────────────────────────────────────────────

export interface AppConfig {
  paperless_url: string;
  paperless_token: string;
  llm_provider: string;
  llm_base_url: string;
  llm_api_key: string;
  llm_model: string;
  embedding_provider: string;
  embedding_base_url: string;
  embedding_api_key: string;
  embedding_model: string;
  webhook_secret: string;
}

export async function getConfig(): Promise<AppConfig> {
  return request<AppConfig>("/config");
}

export async function saveConfig(data: Partial<AppConfig>): Promise<{ success: boolean; message: string }> {
  // Strip masked values before saving
  const clean = stripMasked(data);
  return request("/config", {
    method: "POST",
    body: JSON.stringify(clean),
  });
}

// ── Paperless ─────────────────────────────────────────────────────────────────

export interface ConnectionTestResult {
  success: boolean;
  message: string;
  document_count?: number;
  paperless_version?: string;
}

export async function testPaperlessConnection(
  paperless_url: string,
  paperless_token: string
): Promise<ConnectionTestResult> {
  return request("/paperless/test-connection", {
    method: "POST",
    body: JSON.stringify({ paperless_url, paperless_token }),
  });
}

export async function getPaperlessStatus(): Promise<{
  configured: boolean;
  connected: boolean;
  document_count: number;
  message: string;
}> {
  return request("/paperless/status");
}

// ── Indexing ──────────────────────────────────────────────────────────────────

export interface IndexingStatus {
  is_running: boolean;
  total_documents: number;
  processed_documents: number;
  failed_documents: number;
  current_document: string | null;
  message: string;
}

export interface IndexStats {
  indexed_document_count: number;
  total_chunks: number;
  collection_name: string;
}

export async function startIndexing(): Promise<{ success: boolean; message: string }> {
  return request("/index/start", { method: "POST" });
}

export async function getIndexingStatus(): Promise<IndexingStatus> {
  return request("/index/status");
}

export async function getIndexStats(): Promise<IndexStats> {
  return request("/index/stats");
}

// ── RAG Search ────────────────────────────────────────────────────────────────

export interface SearchSource {
  document_id: number;
  document_title: string;
  text: string;
  distance: number;
}

export interface SearchResult {
  answer: string;
  sources: SearchSource[];
  query: string;
}

export async function ragSearch(
  query: string,
  n_results = 5
): Promise<SearchResult> {
  return request("/rag/search", {
    method: "POST",
    body: JSON.stringify({ query, n_results }),
  });
}