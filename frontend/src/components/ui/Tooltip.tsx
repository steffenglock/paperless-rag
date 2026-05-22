/**
 * Info tooltip component – shows a ℹ️ icon with hover text.
 */

import React, { useState } from "react";

interface TooltipProps {
  text: string;
}

const Tooltip: React.FC<TooltipProps> = ({ text }) => {
  const [visible, setVisible] = useState(false);

  return (
    <div className="relative inline-block">
      <button
        type="button"
        onMouseEnter={() => setVisible(true)}
        onMouseLeave={() => setVisible(false)}
        onFocus={() => setVisible(true)}
        onBlur={() => setVisible(false)}
        className="ml-1 text-gray-400 hover:text-primary-600 transition"
        tabIndex={-1}
      >
        <svg className="h-4 w-4 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M13 16h-1v-4h-1m1-4h.01M12 2a10 10 0 100 20A10 10 0 0012 2z" />
        </svg>
      </button>

      {visible && (
        <div className="absolute left-6 top-0 z-50 w-64 rounded-lg border border-gray-200 bg-white p-3 text-xs text-gray-600 shadow-lg">
          {text}
        </div>
      )}
    </div>
  );
};

export default Tooltip;
