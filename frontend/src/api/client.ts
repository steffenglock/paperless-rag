/**
 * API Client for Paperless RAG backend
 */

const API_BASE = "/api";

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
}

export interface SearchSource {
  document_id: number;
  document_title?: string;
  text: string;
  distance: number;
}

export interface SearchResponse {
  answer: string;
  sources: SearchSource[];
}

export async function getConfig(): Promise<AppConfig> {
  const res = await fetch(`${API_BASE}/config`);
  if (!res.ok) throw new Error("Failed to fetch config");
  return res.json();
}

export async function saveConfig(config: AppConfig): Promise<AppConfig> {
  const res = await fetch(`${API_BASE}/config`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  if (!res.ok) throw new Error("Failed to save config");
  return res.json();
}

export async function triggerPullSync(): Promise<{ status: string; processed: number }> {
  const res = await fetch(`${API_BASE}/sync/pull`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to trigger sync");
  return res.json();
}

export async function checkSetupStatus(): Promise<{ is_setup: boolean }> {
  const res = await fetch(`${API_BASE}/setup/status`);
  if (!res.ok) return { is_setup: true }; // Fallback falls die Route nicht existiert
  return res.json();
}

export async function ragSearch(query: string): Promise<SearchResponse> {
  // KORRIGIERTER PFAD: /api/rag/search
  const res = await fetch(`${API_BASE}/rag/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  if (!res.ok) throw new Error("Search failed");
  return res.json();
}

export async function getIndexStats(): Promise<{ 
  total_documents: number; 
  indexed_documents: number;
  indexed_document_count: number; 
  total_chunks: number; 
}> {
  const res = await fetch(`${API_BASE}/index/stats`);
  if (!res.ok) throw new Error("Failed to fetch index stats");
  return res.json();
}

export async function getPaperlessStatus(): Promise<{ connected: boolean }> {
  const res = await fetch(`${API_BASE}/paperless/status`);
  if (!res.ok) throw new Error("Failed to fetch paperless status");
  return res.json();
}

export async function testPaperlessConnection(url: string, token: string): Promise<{ success: boolean; message: string }> {
  // KORRIGIERTER PFAD: /api/paperless/test-connection
  const res = await fetch(`${API_BASE}/paperless/test-connection`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, token }),
  });
  if (!res.ok) throw new Error("Connection test failed");
  return res.json();
}

export async function startIndexing(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/index/start`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to start indexing");
  return res.json();
}

export async function getIndexingStatus(): Promise<{ status: string; progress: number; message: string; is_running: boolean }> {
  const res = await fetch(`${API_BASE}/index/status`);
  if (!res.ok) throw new Error("Failed to fetch indexing status");
  return res.json();
}
