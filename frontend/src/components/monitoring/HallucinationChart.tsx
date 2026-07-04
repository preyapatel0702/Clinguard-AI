import { memo } from "react";
import Chart from "react-apexcharts";
import { ApexOptions } from "apexcharts";
import ComponentCard from "../common/ComponentCard";
import MonitoringChartEmptyState from "./MonitoringChartEmptyState";
import type { HallucinationTrendPoint } from "../../types/monitoring";

interface HallucinationChartProps {
  data: HallucinationTrendPoint[];
}

function HallucinationChart({ data }: HallucinationChartProps) {
  if (data.length === 0) {
    return (
      <ComponentCard
        title="Hallucination Trend"
        desc="Flagged hallucinations and rate over time"
      >
        <MonitoringChartEmptyState message="No hallucination data for this range." />
      </ComponentCard>
    );
  }

  const options: ApexOptions = {
    legend: {
      show: true,
      position: "top",
      horizontalAlign: "left",
    },
    colors: ["#F04438", "#F79009"],
    chart: {
      fontFamily: "Outfit, sans-serif",
      height: 300,
      type: "bar",
      toolbar: { show: false },
      stacked: false,
    },
    plotOptions: {
      bar: { columnWidth: "45%", borderRadius: 4 },
    },
    stroke: {
      curve: "smooth",
      width: [0, 2],
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
        title: { text: "Count" },
        labels: { style: { fontSize: "12px", colors: ["#6B7280"] } },
      },
      {
        opposite: true,
        title: { text: "Rate (%)" },
        labels: {
          formatter: (value) => `${value.toFixed(0)}%`,
          style: { fontSize: "12px", colors: ["#6B7280"] },
        },
      },
    ],
  };

  const series = [
    {
      name: "Hallucinations",
      type: "bar",
      data: data.map((point) => point.count),
    },
    {
      name: "Rate (%)",
      type: "line",
      data: data.map((point) => point.ratePct),
    },
  ];

  return (
    <ComponentCard
      title="Hallucination Trend"
      desc="Flagged hallucinations and rate over time"
    >
      <div className="max-w-full overflow-x-auto custom-scrollbar">
        <div className="min-w-[600px]">
          <Chart options={options} series={series} type="line" height={300} />
        </div>
      </div>
    </ComponentCard>
  );
}

export default memo(HallucinationChart);
