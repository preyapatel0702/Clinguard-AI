import { memo } from "react";
import Chart from "react-apexcharts";
import { ApexOptions } from "apexcharts";
import ComponentCard from "../common/ComponentCard";
import type { ComplianceTrendPoint } from "../../types";

interface ComplianceTrendChartProps {
  data: ComplianceTrendPoint[];
}

function ComplianceTrendChart({ data }: ComplianceTrendChartProps) {
  const options: ApexOptions = {
    legend: {
      show: true,
      position: "top",
      horizontalAlign: "left",
    },
    colors: ["#465FFF", "#F04438"],
    chart: {
      fontFamily: "Outfit, sans-serif",
      height: 300,
      type: "line",
      toolbar: { show: false },
    },
    stroke: {
      curve: "smooth",
      width: [3, 2],
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
        title: { text: "" },
        labels: {
          formatter: (value) => `${value.toFixed(0)}%`,
          style: { fontSize: "12px", colors: ["#6B7280"] },
        },
      },
    ],
  };

  const series = [
    {
      name: "Compliance Score",
      data: data.map((point) => point.complianceScore),
    },
    {
      name: "Incidents",
      data: data.map((point) => point.incidents),
    },
  ];

  return (
    <ComponentCard
      title="Compliance Trend"
      desc="Monthly compliance score vs. reported incidents"
    >
      <div className="max-w-full overflow-x-auto custom-scrollbar">
        <div className="min-w-[600px]">
          <Chart options={options} series={series} type="area" height={300} />
        </div>
      </div>
    </ComponentCard>
  );
}

export default memo(ComplianceTrendChart);
