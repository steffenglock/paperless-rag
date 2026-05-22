/**
 * Setup wizard – Step 1: Paperless-ngx connection.
 */

import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import ConnectionBadge from "@/components/ui/ConnectionBadge";
import Tooltip from "@/components/ui/Tooltip";
import { testPaperlessConnection } from "@/api/client";
import type { ConnectionStatus, SetupState } from "@/types";

interface Props {
  data: SetupState;
  onChange: (data: Partial<SetupState>) => void;
  onNext: () => void;
}

const StepPaperless: React.FC<Props> = ({ data, onChange, onNext }) => {
  const { t } = useTranslation();
  const [status, setStatus] = useState<ConnectionStatus>("idle");
  const [message, setMessage] = useState("");

  const handleTest = async () => {
    setStatus("testing");
    try {
      const result = await testPaperlessConnection(
        data.paperless_url,
        data.paperless_token
      );
      setStatus(result.success ? "success" : "error");
      setMessage(result.message);
    } catch (e: any) {
      setStatus("error");
      setMessage(e.message);
    }
  };

  const canProceed =
    data.paperless_url.trim() !== "" && data.paperless_token.trim() !== "";

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-xl font-semibold text-gray-800 flex items-center">
          {t("setup.paperless.title")}
          <Tooltip text="Paperless-ngx ist dein Dokumenten-Management-System. Hier gibst du die Adresse deiner Paperless-Instanz und einen API-Token ein, damit Paperless RAG deine Dokumente lesen kann. Den Token findest du in Paperless unter: Einstellungen → Profil → API Token." />
        </h2>
        <p className="mt-1 text-sm text-gray-500">
          {t("setup.paperless.description")}
        </p>
      </div>

      <div className="flex flex-col gap-4">
        <Input
          label={t("setup.paperless.url")}
          placeholder={t("setup.paperless.urlPlaceholder")}
          value={data.paperless_url}
          onChange={(e) => onChange({ paperless_url: e.target.value })}
          type="url"
        />
        <Input
          label={t("setup.paperless.token")}
          placeholder={t("setup.paperless.tokenPlaceholder")}
          helpText={t("setup.paperless.tokenHelp")}
          value={data.paperless_token}
          onChange={(e) => onChange({ paperless_token: e.target.value })}
          type="password"
        />
      </div>

      <div className="flex flex-col gap-2">
        <Button
          variant="secondary"
          onClick={handleTest}
          loading={status === "testing"}
          disabled={!canProceed}
        >
          {t("setup.test")}
        </Button>
        <ConnectionBadge status={status} message={message} />
      </div>

      <div className="flex justify-end">
        <Button onClick={onNext} disabled={!canProceed}>
          {t("setup.next")}
        </Button>
      </div>
    </div>
  );
};

export default StepPaperless;