/**
 * Setup wizard container.
 * Manages step navigation and shared state.
 */

import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import StepPaperless from "./StepPaperless";
import StepEmbedding from "./StepEmbedding";
import StepLLM from "./StepLLM";
import StepDone from "./StepDone";
import { saveConfig } from "@/api/client";
import type { SetupState } from "@/types";

const STEP_KEYS = ["paperless", "embedding", "llm", "done"] as const;

const DEFAULT_STATE: SetupState = {
  paperless_url: "",
  paperless_token: "",
  embedding_provider: "openrouter",
  embedding_base_url: "https://openrouter.ai/api/v1",
  embedding_api_key: "",
  embedding_model: "",
  llm_provider: "openrouter",
  llm_base_url: "https://openrouter.ai/api/v1",
  llm_api_key: "",
  llm_model: "",
};

interface Props {
  onDone: () => void;
}

const SetupWizard: React.FC<Props> = ({ onDone }) => {
  const { t } = useTranslation();
  const [step, setStep] = useState(0);
  const [state, setState] = useState<SetupState>(DEFAULT_STATE);
  const [saving, setSaving] = useState(false);

  const updateState = (data: Partial<SetupState>) => {
    setState((prev) => ({ ...prev, ...data }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await saveConfig({
        paperless_url: state.paperless_url,
        paperless_token: state.paperless_token,
        embedding_provider: state.embedding_provider,
        embedding_base_url: state.embedding_base_url,
        embedding_api_key: state.embedding_api_key,
        embedding_model: state.embedding_model,
        llm_provider: state.llm_provider,
        llm_base_url: state.llm_base_url,
        llm_api_key: state.llm_api_key,
        llm_model: state.llm_model,
      });
    } finally {
      setSaving(false);
    }
  };

  const next = () => setStep((s) => Math.min(s + 1, STEP_KEYS.length - 1));
  const back = () => setStep((s) => Math.max(s - 1, 0));

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
      <div className="w-full max-w-lg">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-primary-700">
            {t("app.title")}
          </h1>
          <p className="mt-1 text-gray-500">{t("setup.subtitle")}</p>
        </div>

        {/* Step indicator */}
        <div className="mb-8 flex items-center justify-center gap-2">
          {STEP_KEYS.map((key, i) => (
            <React.Fragment key={key}>
              <div
                className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold transition
                  ${i <= step
                    ? "bg-primary-600 text-white"
                    : "bg-gray-200 text-gray-500"
                  }`}
              >
                {i + 1}
              </div>
              {i < STEP_KEYS.length - 1 && (
                <div
                  className={`h-0.5 w-12 transition ${
                    i < step ? "bg-primary-600" : "bg-gray-200"
                  }`}
                />
              )}
            </React.Fragment>
          ))}
        </div>

        {/* Step label */}
        <p className="mb-4 text-center text-sm text-gray-500">
          {t("setup.step")} {step + 1} {t("setup.of")} {STEP_KEYS.length} –{" "}
          <span className="font-medium text-gray-700">
            {t(`setup.steps.${STEP_KEYS[step]}`)}
          </span>
        </p>

        {/* Card */}
        <div className="rounded-2xl bg-white p-8 shadow-lg">
          {step === 0 && (
            <StepPaperless
              data={state}
              onChange={updateState}
              onNext={next}
            />
          )}
          {step === 1 && (
            <StepEmbedding
              data={state}
              onChange={updateState}
              onNext={next}
              onBack={back}
            />
          )}
          {step === 2 && (
            <StepLLM
              data={state}
              onChange={updateState}
              onNext={next}
              onBack={back}
              onSave={handleSave}
              saving={saving}
            />
          )}
          {step === 3 && <StepDone onDone={onDone} />}
        </div>
      </div>
    </div>
  );
};

export default SetupWizard;