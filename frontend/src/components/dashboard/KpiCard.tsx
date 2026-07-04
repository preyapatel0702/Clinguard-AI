import { memo } from "react";
import { ArrowDownIcon, ArrowUpIcon } from "../../icons";
import type { KpiStat } from "../../types";

interface KpiCardProps {
  stat: KpiStat;
}

function KpiCard({ stat }: KpiCardProps) {
  const trendColor =
    stat.trend === "up"
      ? "text-success-600 dark:text-success-500"
      : stat.trend === "down"
      ? "text-error-600 dark:text-error-500"
      : "text-gray-500 dark:text-gray-400";

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-5 transition-shadow duration-200 hover:shadow-theme-sm dark:border-gray-800 dark:bg-white/[0.03] md:p-6">
      <p className="text-sm text-gray-500 dark:text-gray-400">{stat.label}</p>

      <div className="mt-2 flex items-end justify-between">
        <h4 className="text-title-sm font-bold text-gray-800 dark:text-white/90">
          {stat.value}
          {stat.unit && (
            <span className="ml-1 text-base font-medium text-gray-500 dark:text-gray-400">
              {stat.unit}
            </span>
          )}
        </h4>

        {stat.change && (
          <span className={`flex items-center gap-1 text-sm font-medium ${trendColor}`}>
            {stat.trend === "up" && <ArrowUpIcon className="size-4" />}
            {stat.trend === "down" && <ArrowDownIcon className="size-4" />}
            {stat.change}
          </span>
        )}
      </div>

      {stat.helpText && (
        <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">{stat.helpText}</p>
      )}
    </div>
  );
}

export default memo(KpiCard);
