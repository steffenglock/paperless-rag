/**
 * Setup wizard – Step 4: Done.
 */

import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import Button from "@/components/ui/Button";
import { startIndexing, getIndexingStatus } from "@/api/client";

interface Props {
  onDone: () => void;
}

const StepDone: React.FC<Props> = ({ onDone }) => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [indexing, setIndexing] = useState(false);
  const [indexMessage, setIndexMessage] = useState("");

  const handleIndex = async () => {
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
        }
      }, 2000);
    } catch (e: any) {
      setIndexMessage(e.message);
      setIndexing(false);
    }
  };

  const handleGoToSearch = () => {
    onDone();
    navigate("/");
  };

  return (
    <div className="flex flex-col items-center gap-6 text-center">
      <div className="flex h-20 w-20 items-center justify-center rounded-full bg-green-100">
        <span className="text-4xl">✅</span>
      </div>

      <div>
        <h2 className="text-2xl font-bold text-gray-800">
          {t("setup.done.title")}
        </h2>
        <p className="mt-2 text-gray-500">{t("setup.done.description")}</p>
      </div>

      <div className="flex flex-col gap-3 w-full max-w-xs">
        <Button onClick={handleIndex} loading={indexing} variant="secondary">
          {indexing ? t("setup.done.indexing") : t("setup.done.indexButton")}
        </Button>

        {indexMessage && (
          <p className="text-sm text-gray-600 bg-gray-50 rounded-lg px-3 py-2">
            {indexMessage}
          </p>
        )}

        <Button onClick={handleGoToSearch}>
          {t("setup.done.goToSearch")}
        </Button>
      </div>
    </div>
  );
};

export default StepDone;