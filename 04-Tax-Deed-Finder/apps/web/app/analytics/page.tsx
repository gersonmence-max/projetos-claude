"use client";
import { useQuery } from "@tanstack/react-query";
import { fetchAnalytics } from "@/lib/api";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

const COLORS = ["#e5e7eb", "#d1d5db", "#fbbf24", "#3b82f6", "#22c55e"];

export default function AnalyticsPage() {
  const { data, isLoading } = useQuery({ queryKey: ["analytics"], queryFn: fetchAnalytics });

  if (isLoading) {
    return <div className="text-center py-20 text-gray-400">Carregando analytics...</div>;
  }

  const scoreData = data?.score_distribution
    ? Object.entries(data.score_distribution as Record<string, number>).map(([range, count], i) => ({
        range,
        count,
        color: COLORS[i] || "#6b7280",
      }))
    : [];

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Analytics</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="text-sm text-gray-500">Total analisados</div>
          <div className="text-3xl font-bold mt-1">{data?.total_scored ?? "—"}</div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="text-sm text-gray-500">Score 70+ (alta qualidade)</div>
          <div className="text-3xl font-bold mt-1 text-blue-600">
            {(data?.score_distribution?.["70-84"] ?? 0) + (data?.score_distribution?.["85-100"] ?? 0)}
          </div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="text-sm text-gray-500">Taxa aprovação (score ≥ 50)</div>
          <div className="text-3xl font-bold mt-1 text-green-600">
            {data?.total_scored
              ? `${(((data.score_distribution?.["50-69"] ?? 0) +
                  (data.score_distribution?.["70-84"] ?? 0) +
                  (data.score_distribution?.["85-100"] ?? 0)) /
                  data.total_scored * 100).toFixed(1)}%`
              : "—"}
          </div>
        </div>
      </div>

      {/* Score distribution chart */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
        <h2 className="font-semibold text-gray-900 mb-4">Distribuição de scores</h2>
        {scoreData.length > 0 ? (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={scoreData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <XAxis dataKey="range" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip formatter={(v) => [`${v} imóveis`, "Quantidade"]} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {scoreData.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-48 flex items-center justify-center text-gray-400 text-sm">
            Sem dados suficientes ainda. Execute o pipeline para popular.
          </div>
        )}
      </div>

      {/* Score legend */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h2 className="font-semibold text-gray-900 mb-4">Legenda dos scores</h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {[
            { range: "0-24", label: "Muito baixo", color: "bg-gray-200" },
            { range: "25-49", label: "Baixo", color: "bg-gray-300" },
            { range: "50-69", label: "Médio", color: "bg-yellow-400" },
            { range: "70-84", label: "Alto", color: "bg-blue-500" },
            { range: "85-100", label: "Excelente", color: "bg-green-500" },
          ].map(({ range, label, color }) => (
            <div key={range} className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${color}`} />
              <div>
                <div className="text-sm font-medium">{range}</div>
                <div className="text-xs text-gray-500">{label}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
