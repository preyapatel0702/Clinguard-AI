import { memo } from "react";
import Chart from "react-apexcharts";
import { ApexOptions } from "apexcharts";
import ComponentCard from "../common/ComponentCard";
import MonitoringChartEmptyState from "./MonitoringChartEmptyState";
import type { ValidationTrendPoint } from "../../types/monitoring";

interface ValidationChartProps {
  data: ValidationTrendPoint[];
}

function ValidationChart({ data }: ValidationChartProps) {
  if (data.length === 0) {
    return (
      <ComponentCard
        title="Validation Accuracy"
        desc="Pass rate and failure count over time"
      >
        <MonitoringChartEmptyState message="No validation data for this range." />
      </ComponentCard>
    );
  }

  const options: ApexOptions = {
    legend: {
      show: true,
      position: "top",
      horizontalAlign: "left",
    },
    colors: ["#12B76A", "#F04438"],
    chart: {
      fontFamily: "Outfit, sans-serif",
      height: 300,
      type: "line",
      toolbar: { show: false },
    },
    stroke: {
      curve: "smooth",
      width: [3, 0],
    },
    fill: {
      type: "gradient",
      gradient: { opacityFrom: 0.35, opacityTo: 0 },
    },
    markers: {
      size: 0,
      strokeColors: "#fff",
      strokeWidth: 2,
      hover: { size: 6 },
    },
    plotOptions: {
      bar: { columnWidth: "35%", borderRadius: 4 },
    },
    grid: {
      xaxis: { lines: { show: false } },
      yaxis: { lines: { show: true } },
    },
    dataLabels: { enabled: false },
    tooltip: { enabled: true },
    xaxis: {
      type: "category",
      categories: data.map((point) => point.label),
      axisBorder: { show: false },
      axisTicks: { show: false },
    },
    yaxis: [
      {
        title: { text: "Pass rate (%)" },
        labels: {
          formatter: (value) => `${value.toFixed(0)}%`,
          style: { fontSize: "12px", colors: ["#6B7280"] },
        },
      },
      {
        opposite: true,
        title: { text: "Failures" },
        labels: { style: { fontSize: "12px", colors: ["#6B7280"] } },
      },
    ],
  };

  const series = [
    {
      name: "Pass rate (%)",
      type: "area",
      data: data.map((point) => point.passRatePct),
    },
    {
      name: "Failures",
      type: "bar",
      data: data.map((point) => point.failCount),
    },
  ];

  return (
    <ComponentCard
      title="Validation Accuracy"
      desc="Pass rate and failure count over time"
    >
      <div className="max-w-full overflow-x-auto custom-scrollbar">
        <div className="min-w-[600px]">
          <Chart options={options} series={series} type="line" height={300} />
        </div>
      </div>
    </ComponentCard>
  );
}

export default memo(ValidationChart);
