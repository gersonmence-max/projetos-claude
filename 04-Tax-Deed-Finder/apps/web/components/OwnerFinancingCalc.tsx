"use client";
import { useState, useMemo } from "react";
import { formatCurrency } from "@/lib/api";

interface Props {
  minimumBid: number;
  marketValue: number;
}

export default function OwnerFinancingCalc({ minimumBid, marketValue }: Props) {
  const [resaleRatio, setResaleRatio] = useState(65);
  const [downPct, setDownPct] = useState(10);
  const [termMonths, setTermMonths] = useState(24);

  const calc = useMemo(() => {
    const resalePrice = marketValue * (resaleRatio / 100);
    const down = resalePrice * (downPct / 100);
    const balance = resalePrice - down;
    const monthly = termMonths > 0 ? balance / termMonths : 0;
    const total = down + monthly * termMonths;
    const roi = minimumBid > 0 ? ((total / minimumBid) - 1) * 100 : 0;
    const recover = monthly > 0 ? minimumBid / monthly : 0;
    return { resalePrice, down, balance, monthly, total, roi, recover };
  }, [minimumBid, marketValue, resaleRatio, downPct, termMonths]);

  return (
    <div className="bg-blue-50 rounded-xl p-5">
      <h3 className="font-semibold text-blue-900 mb-4">Calculadora Owner Financing</h3>

      <div className="grid grid-cols-3 gap-4 mb-5">
        <div>
          <label className="block text-xs font-medium text-blue-700 mb-1">
            Preço de revenda: {resaleRatio}% do mercado
          </label>
          <input type="range" min={40} max={90} step={5} value={resaleRatio}
            onChange={(e) => setResaleRatio(Number(e.target.value))}
            className="w-full" />
        </div>
        <div>
          <label className="block text-xs font-medium text-blue-700 mb-1">
            Entrada: {downPct}%
          </label>
          <input type="range" min={5} max={30} step={5} value={downPct}
            onChange={(e) => setDownPct(Number(e.target.value))}
            className="w-full" />
        </div>
        <div>
          <label className="block text-xs font-medium text-blue-700 mb-1">
            Prazo: {termMonths} meses
          </label>
          <input type="range" min={12} max={60} step={6} value={termMonths}
            onChange={(e) => setTermMonths(Number(e.target.value))}
            className="w-full" />
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Preço de revenda", value: formatCurrency(calc.resalePrice) },
          { label: "Entrada (10%)", value: formatCurrency(calc.down) },
          { label: "Parcela mensal", value: formatCurrency(calc.monthly) },
          { label: "Retorno total", value: formatCurrency(calc.total) },
          { label: "ROI", value: `${calc.roi.toFixed(0)}%`, highlight: true },
          { label: "Meses p/ recuperar", value: `${calc.recover.toFixed(0)} meses` },
          { label: "Custo aquisição", value: formatCurrency(minimumBid) },
          { label: "Vlr. mercado", value: formatCurrency(marketValue) },
        ].map(({ label, value, highlight }) => (
          <div key={label} className="bg-white rounded-lg p-3">
            <div className="text-xs text-gray-500">{label}</div>
            <div className={`text-base font-bold mt-0.5 ${highlight ? "text-blue-700" : "text-gray-900"}`}>
              {value}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
