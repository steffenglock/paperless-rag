/**
 * Settings page with connection tests and indexing controls.
 */

import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import Layout from "@/components/Layout";
import Input from "@/components/ui/Input";
import Select from "@/components/ui/Select";
import Button from "@/components/ui/Button";
import ConnectionBadge from "@/components/ui/ConnectionBadge";
import Tooltip from "@/components/ui/Tooltip";
import {
  getConfig,
  saveConfig,
  testPaperlessConnection,
  startIndexing,
  getIndexingStatus,
  getIndexStats,
  type AppConfig,
} from "@/api/client";
import type { ConnectionStatus, Provider } from "@/types";

// ── Provider URL defaults ─────────────────────────────────────────────────────
const PROVIDER_URLS: Record<Provider, string> = {
  ollama: "http://localhost:11434",
  openai: "https://api.openai.com/v1",
  openrouter: "https://openrouter.ai/api/v1",
};

// ── Section component with optional tooltip ───────────────────────────────────
const Section: React.FC<{
  title: string;
  tooltip?: string;
  children: React.ReactNode;
}> = ({ title, tooltip, children }) => (
  <div className="rounded-2xl bg-white p-6 shadow-sm border border-gray-100">
    <h2 className="mb-4 text-base font-semibold text-gray-800 flex items-center">
      {title}
      {tooltip && <Tooltip text={tooltip} />}
    </h2>
    {children}
  </div>
);

// ── Main Settings Page ────────────────────────────────────────────────────────
const SettingsPage: React.FC = () => {
  const { t } = useTranslation();

  const [config, setConfig] = useState<AppConfig>({
    paperless_url: "",
    paperless_token: "",
    llm_provider: "openrouter",
    llm_base_url: "https://openrouter.ai/api/v1",
    llm_api_key: "",
    llm_model: "",
    embedding_provider: "openrouter",
    embedding_base_url: "https://openrouter.ai/api/v1",
    embedding_api_key: "",
    embedding_model: "",
  });

  const [savedFields, setSavedFields] = useState<Record<string, boolean>>({});
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState("");
  const [paperlessStatus, setPaperlessStatus] = useState<ConnectionStatus>("idle");
  const [paperlessMessage, setPaperlessMessage] = useState("");
  const [indexing, setIndexing] = useState(false);
  const [indexMessage, setIndexMessage] = useState("");
  const [indexStats, setIndexStats] = useState<{
    indexed_document_count: number;
    total_chunks: number;
  } | null>(null);

  useEffect(() => {
    getConfig().then((c) => {
      setSavedFields({
        paperless_token: c.paperless_token?.includes("•") || false,
        llm_api_key: c.llm_api_key?.includes("•") || false,
        embedding_api_key: c.embedding_api_key?.includes("•") || false,
      });
      setConfig({
        ...c,
        paperless_token: c.paperless_token?.includes("•") ? "" : c.paperless_token,
        llm_api_key: c.llm_api_key?.includes("•") ? "" : c.llm_api_key,
        embedding_api_key: c.embedding_api_key?.includes("•") ? "" : c.embedding_api_key,
      });
    }).catch(() => {});
    getIndexStats().then(setIndexStats).catch(() => {});
  }, []);

  const update = (data: Partial<AppConfig>) => {
    setConfig((prev) => ({ ...prev, ...data }));
  };

  const handleSave = async () => {
    setSaving(true);
    setSaveMessage("");
    try {
      const payload = { ...config };
      
      if (payload.paperless_token === "" && savedFields.paperless_token) {
        delete (payload as any).paperless_token;
      }
      if (payload.llm_api_key === "" && savedFields.llm_api_key) {
        delete (payload as any).llm_api_key;
      }
      if (payload.embedding_api_key === "" && savedFields.embedding_api_key) {
        delete (payload as any).embedding_api_key;
      }

      await saveConfig(payload);
      setSaveMessage("✅ " + t("settings.saved"));
      
      setSavedFields({
        paperless_token: config.paperless_token !== "" || savedFields.paperless_token,
        llm_api_key: config.llm_api_key !== "" || savedFields.llm_api_key,
        embedding_api_key: config.embedding_api_key !== "" || savedFields.embedding_api_key,
      });
      
      setTimeout(() => setSaveMessage(""), 3000);
    } catch (e: any) {
      setSaveMessage("❌ " + e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleTestPaperless = async () => {
    setPaperlessStatus("testing");
    try {
      const result = await testPaperlessConnection(
        config.paperless_url,
        config.paperless_token
      );
      setPaperlessStatus(result.success ? "success" : "error");
      setPaperlessMessage(result.message);
    } catch (e: any) {
      setPaperlessStatus("error");
      setPaperlessMessage(e.message);
    }
  };

  const handleStartIndexing = async () => {
    setIndexing(true);
    setIndexMessage("");
    try {
      await startIndexing();
      const interval = setInterval(async () => {
        const status = await getIndexingStatus();
        setIndexMessage(status.message);
        if (!status.is_running) {
          clearInterval(interval);
          setIndexing(false);
          getIndexStats().then(setIndexStats).catch(() => {});
        }
      }, 2000);
    } catch (e: any) {
      setIndexMessage(e.message);
      setIndexing(false);
    }
  };

  const providerOptions = [
    { value: "ollama", label: t("setup.providers.ollama") },
    { value: "openai", label: t("setup.providers.openai") },
    { value: "openrouter", label: t("setup.providers.openrouter") },
  ];

  const savedPlaceholder = t("settings.savedPlaceholder");

  return (
    <Layout>
      <div className="mx-auto max-w-2xl px-4 py-8 flex flex-col gap-6">
        <h1 className="text-2xl font-bold text-gray-800">
          {t("settings.title")}
        </h1>

        {/* ── Paperless-ngx ─────────────────────────────────────────────── */}
        <Section
          title="Paperless-ngx"
          tooltip={t("settings.tooltips.paperless")}
        >
          <div className="flex flex-col gap-4">
            <Input
              label={t("setup.paperless.url")}
              placeholder={t("setup.paperless.urlPlaceholder")}
              value={config.paperless_url}
              onChange={(e) => update({ paperless_url: e.target.value })}
              type="url"
            />
            <Input
              label={t("setup.paperless.token")}
              placeholder={
                savedFields.paperless_token
                  ? savedPlaceholder
                  : t("setup.paperless.tokenPlaceholder")
              }
              helpText={t("setup.paperless.tokenHelp")}
              value={config.paperless_token}
              onChange={(e) => update({ paperless_token: e.target.value })}
              type="password"
            />
            <div>
              <Button
                variant="secondary"
                onClick={handleTestPaperless}
                loading={paperlessStatus === "testing"}
              >
                {t("settings.test")}
              </Button>
              <ConnectionBadge
                status={paperlessStatus}
                message={paperlessMessage}
              />
            </div>
          </div>
        </Section>

        {/* ── Embedding ─────────────────────────────────────────────────── */}
        <Section
          title="Embeddings"
          tooltip={t("settings.tooltips.embedding")}
        >
          <div className="flex flex-col gap-4">
            <Select
              label={t("setup.embedding.provider")}
              options={providerOptions}
              value={config.embedding_provider}
              onChange={(e) => {
                const p = e.target.value as Provider;
                update({
                  embedding_provider: p,
                  embedding_base_url: PROVIDER_URLS[p],
                });
              }}
            />
            <Input
              label={t("setup.embedding.baseUrl")}
              value={config.embedding_base_url}
              onChange={(e) => update({ embedding_base_url: e.target.value })}
              type="url"
            />
            {config.embedding_provider !== "ollama" && (
              <Input
                label={t("setup.embedding.apiKey")}
                placeholder={
                  savedFields.embedding_api_key ? savedPlaceholder : "sk-…"
                }
                value={config.embedding_api_key}
                onChange={(e) => update({ embedding_api_key: e.target.value })}
                type="password"
              />
            )}
            <Input
              label={t("setup.embedding.model")}
              placeholder={t("setup.embedding.modelPlaceholder")}
              value={config.embedding_model}
              onChange={(e) => update({ embedding_model: e.target.value })}
            />
          </div>
        </Section>

        {/* ── LLM ───────────────────────────────────────────────────────── */}
        <Section
          title={t("setup.llm.title")}
          tooltip={t("settings.tooltips.llm")}
        >
          <div className="flex flex-col gap-4">
            <Select
              label={t("setup.llm.provider")}
              options={providerOptions}
              value={config.llm_provider}
              onChange={(e) => {
                const p = e.target.value as Provider;
                update({
                  llm_provider: p,
                  llm_base_url: PROVIDER_URLS[p],
                });
              }}
            />
            <Input
              label={t("setup.llm.baseUrl")}
              value={config.llm_base_url}
              onChange={(e) => update({ llm_base_url: e.target.value })}
              type="url"
            />
            {config.llm_provider !== "ollama" && (
              <Input
                label={t("setup.llm.apiKey")}
                placeholder={
                  savedFields.llm_api_key ? savedPlaceholder : "sk-…"
                }
                value={config.llm_api_key}
                onChange={(e) => update({ llm_api_key: e.target.value })}
                type="password"
              />
            )}
            <Input
              label={t("setup.llm.model")}
              placeholder={t("setup.llm.modelPlaceholder")}
              value={config.llm_model}
              onChange={(e) => update({ llm_model: e.target.value })}
            />
          </div>
        </Section>

        {/* ── Indexing ──────────────────────────────────────────────────── */}
        <Section
          title={t("settings.reindex")}
          tooltip={t("settings.tooltips.indexing")}
        >
          <div className="flex flex-col gap-4">
            {indexStats && (
              <div className="flex gap-4 rounded-lg bg-primary-50 px-4 py-3 text-sm">
                <span className="text-primary-700">
                  📄 {t("status.indexed", { count: indexStats.indexed_document_count })}
                </span>
                <span className="text-primary-700">
                  🧩 {t("status.chunks", { count: indexStats.total_chunks })}
                </span>
              </div>
            )}
            <Button
              onClick={handleStartIndexing}
              loading={indexing}
              variant="secondary"
            >
              {indexing ? t("settings.reindexing") : t("settings.reindex")}
            </Button>
            {indexMessage && (
              <p className="rounded-lg bg-gray-50 border border-gray-100 px-3 py-2 text-sm text-gray-600">
                {indexMessage}
              </p>
            )}
          </div>
        </Section>

        {/* ── Save button ───────────────────────────────────────────────── */}
        <div className="flex items-center justify-between">
          {saveMessage && (
            <p className="text-sm text-gray-600">{saveMessage}</p>
          )}
          <div className="ml-auto">
            <Button onClick={handleSave} loading={saving}>
              {saving ? t("setup.saving") : t("settings.save")}
            </Button>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default SettingsPage;
