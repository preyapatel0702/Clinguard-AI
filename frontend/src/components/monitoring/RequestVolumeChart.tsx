import { memo } from "react";
import Chart from "react-apexcharts";
import { ApexOptions } from "apexcharts";
import ComponentCard from "../common/ComponentCard";
import MonitoringChartEmptyState from "./MonitoringChartEmptyState";
import type { RequestVolumePoint } from "../../types/monitoring";

interface RequestVolumeChartProps {
  data: RequestVolumePoint[];
}

function RequestVolumeChart({ data }: RequestVolumeChartProps) {
  if (data.length === 0) {
    return (
      <ComponentCard
        title="Request Volume"
        desc="Requests handled and average latency over time"
      >
        <MonitoringChartEmptyState message="No request volume data for this range." />
      </ComponentCard>
    );
  }

  const options: ApexOptions = {
    legend: {
      show: true,
      position: "top",
      horizontalAlign: "left",
    },
    colors: ["#465FFF", "#0BA5EC"],
    chart: {
      fontFamily: "Outfit, sans-serif",
      height: 300,
      type: "bar",
      toolbar: { show: false },
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
        title: { text: "Requests" },
        labels: { style: { fontSize: "12px", colors: ["#6B7280"] } },
      },
      {
        opposite: true,
        title: { text: "Avg latency (ms)" },
        labels: { style: { fontSize: "12px", colors: ["#6B7280"] } },
      },
    ],
  };

  const series = [
    {
      name: "Requests",
      type: "bar",
      data: data.map((point) => point.requests),
    },
    {
      name: "Avg latency (ms)",
      type: "line",
      data: data.map((point) => point.avgLatencyMs),
    },
  ];

  return (
    <ComponentCard
      title="Request Volume"
      desc="Requests handled and average latency over time"
    >
      <div className="max-w-full overflow-x-auto custom-scrollbar">
        <div className="min-w-[600px]">
          <Chart options={options} series={series} type="line" height={300} />
        </div>
      </div>
    </ComponentCard>
  );
}

export default memo(RequestVolumeChart);
