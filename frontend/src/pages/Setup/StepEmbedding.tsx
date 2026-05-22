/**
 * Setup wizard – Step 2: Embedding configuration.
 */

import React from "react";
import { useTranslation } from "react-i18next";
import Input from "@/components/ui/Input";
import Select from "@/components/ui/Select";
import Button from "@/components/ui/Button";
import Tooltip from "@/components/ui/Tooltip";
import type { Provider, SetupState } from "@/types";

interface Props {
  data: SetupState;
  onChange: (data: Partial<SetupState>) => void;
  onNext: () => void;
  onBack: () => void;
}

// Default URLs per provider
const PROVIDER_URLS: Record<Provider, string> = {
  ollama: "http://localhost:11434",
  openai: "https://api.openai.com/v1",
  openrouter: "https://openrouter.ai/api/v1",
};

const StepEmbedding: React.FC<Props> = ({ data, onChange, onNext, onBack }) => {
  const { t } = useTranslation();

  const providerOptions = [
    { value: "ollama", label: t("setup.providers.ollama") },
    { value: "openai", label: t("setup.providers.openai") },
    { value: "openrouter", label: t("setup.providers.openrouter") },
  ];

  const handleProviderChange = (provider: Provider) => {
    onChange({
      embedding_provider: provider,
      embedding_base_url: PROVIDER_URLS[provider],
    });
  };

  const canProceed =
    data.embedding_model.trim() !== "" &&
    data.embedding_base_url.trim() !== "";

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-800 flex items-center">
          {t("setup.embedding.title")}
          <Tooltip text="Embeddings wandeln Text in Zahlen um, damit der Computer verstehen kann welche Texte inhaltlich ähnlich sind. Du brauchst einen Anbieter der diese Umwandlung durchführt. Ollama läuft lokal auf deinem Rechner (kostenlos), OpenAI und OpenRouter sind Online-Dienste (kostenpflichtig, aber sehr gut). Das Modell 'nomic-embed-text' (Ollama) oder 'openai/text-embedding-3-small' (OpenRouter) sind gute Startpunkte." />
        </h2>
        <p className="mt-1 text-sm text-gray-500">
          {t("setup.embedding.description")}
        </p>
      </div>

      <div className="flex flex-col gap-4">
        <Select
          label={t("setup.embedding.provider")}
          options={providerOptions}
          value={data.embedding_provider}
          onChange={(e) => handleProviderChange(e.target.value as Provider)}
        />
        <Input
          label={t("setup.embedding.baseUrl")}
          value={data.embedding_base_url}
          onChange={(e) => onChange({ embedding_base_url: e.target.value })}
          type="url"
        />
        {data.embedding_provider !== "ollama" && (
          <Input
            label={t("setup.embedding.apiKey")}
            value={data.embedding_api_key}
            onChange={(e) => onChange({ embedding_api_key: e.target.value })}
            type="password"
            placeholder="sk-…"
          />
        )}
        <Input
          label={t("setup.embedding.model")}
          placeholder={t("setup.embedding.modelPlaceholder")}
          value={data.embedding_model}
          onChange={(e) => onChange({ embedding_model: e.target.value })}
        />
      </div>

      <div className="flex justify-between">
        <Button variant="secondary" onClick={onBack}>
          {t("setup.back")}
        </Button>
        <Button onClick={onNext} disabled={!canProceed}>
          {t("setup.next")}
        </Button>
      </div>
    </div>
  );
};

export default StepEmbedding;