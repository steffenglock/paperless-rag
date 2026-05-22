/**
 * Setup wizard – Step 3: LLM configuration.
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
  onSave: () => Promise<void>;
  saving: boolean;
}

const PROVIDER_URLS: Record<Provider, string> = {
  ollama: "http://localhost:11434",
  openai: "https://api.openai.com/v1",
  openrouter: "https://openrouter.ai/api/v1",
};

const StepLLM: React.FC<Props> = ({
  data,
  onChange,
  onNext,
  onBack,
  onSave,
  saving,
}) => {
  const { t } = useTranslation();

  const providerOptions = [
    { value: "ollama", label: t("setup.providers.ollama") },
    { value: "openai", label: t("setup.providers.openai") },
    { value: "openrouter", label: t("setup.providers.openrouter") },
  ];

  const handleProviderChange = (provider: Provider) => {
    onChange({
      llm_provider: provider,
      llm_base_url: PROVIDER_URLS[provider],
    });
  };

  const canProceed =
    data.llm_model.trim() !== "" && data.llm_base_url.trim() !== "";

  const handleNext = async () => {
    await onSave();
    onNext();
  };

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-800 flex items-center">
          {t("setup.llm.title")}
          <Tooltip text="Das Sprachmodell (LLM = Large Language Model) ist die KI die deine Fragen beantwortet. Es liest die gefundenen Dokumentausschnitte und formuliert daraus eine verständliche Antwort. Ollama läuft lokal (kostenlos, aber braucht einen leistungsstarken Rechner), OpenRouter gibt dir Zugang zu vielen Modellen wie Claude oder GPT-4 (kostenpflichtig). Für den Anfang empfehlen wir 'anthropic/claude-3.5-haiku' über OpenRouter." />
        </h2>
        <p className="mt-1 text-sm text-gray-500">
          {t("setup.llm.description")}
        </p>
      </div>

      <div className="flex flex-col gap-4">
        <Select
          label={t("setup.llm.provider")}
          options={providerOptions}
          value={data.llm_provider}
          onChange={(e) => handleProviderChange(e.target.value as Provider)}
        />
        <Input
          label={t("setup.llm.baseUrl")}
          value={data.llm_base_url}
          onChange={(e) => onChange({ llm_base_url: e.target.value })}
          type="url"
        />
        {data.llm_provider !== "ollama" && (
          <Input
            label={t("setup.llm.apiKey")}
            value={data.llm_api_key}
            onChange={(e) => onChange({ llm_api_key: e.target.value })}
            type="password"
            placeholder="sk-…"
          />
        )}
        <Input
          label={t("setup.llm.model")}
          placeholder={t("setup.llm.modelPlaceholder")}
          value={data.llm_model}
          onChange={(e) => onChange({ llm_model: e.target.value })}
        />
      </div>

      <div className="flex justify-between">
        <Button variant="secondary" onClick={onBack}>
          {t("setup.back")}
        </Button>
        <Button onClick={handleNext} disabled={!canProceed} loading={saving}>
          {saving ? t("setup.saving") : t("setup.next")}
        </Button>
      </div>
    </div>
  );
};

export default StepLLM;