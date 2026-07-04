import { memo } from "react";
import Chart from "react-apexcharts";
import { ApexOptions } from "apexcharts";
import ComponentCard from "../common/ComponentCard";
import type { SeverityBreakdownPoint } from "../../types";

interface SeverityBreakdownChartProps {
  data: SeverityBreakdownPoint[];
}

const SEVERITY_COLORS: Record<SeverityBreakdownPoint["severity"], string> = {
  critical: "#F04438",
  high: "#F79009",
  medium: "#0BA5EC",
  low: "#12B76A",
  info: "#98A2B3",
};

const SEVERITY_LABELS: Record<SeverityBreakdownPoint["severity"], string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
  info: "Info",
};

function SeverityBreakdownChart({ data }: SeverityBreakdownChartProps) {
  const options: ApexOptions = {
    chart: {
      fontFamily: "Outfit, sans-serif",
      type: "donut",
    },
    labels: data.map((point) => SEVERITY_LABELS[point.severity]),
    colors: data.map((point) => SEVERITY_COLORS[point.severity]),
    legend: {
      position: "bottom",
      fontFamily: "Outfit, sans-serif",
    },
    dataLabels: { enabled: false },
    stroke: { width: 0 },
    plotOptions: {
      pie: {
        donut: {
          size: "70%",
          labels: {
            show: true,
            total: {
              show: true,
              label: "Total Findings",
              fontSize: "13px",
            },
          },
        },
      },
    },
  };

  const series = data.map((point) => point.count);

  return (
    <ComponentCard
      title="Severity Breakdown"
      desc="Open findings across all monitored models"
    >
      <Chart options={options} series={series} type="donut" height={300} />
    </ComponentCard>
  );
}

export default memo(SeverityBreakdownChart);
