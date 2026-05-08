import { floodZoneColor, tornadoColor } from "@/lib/api";
import type { ParcelRisk } from "@/lib/api";

export default function RiskBadges({ risk }: { risk: ParcelRisk | null }) {
  if (!risk) return null;
  return (
    <div className="flex flex-wrap gap-1.5">
      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${floodZoneColor(risk.flood_zone)}`}>
        Flood: {risk.flood_zone}
      </span>
      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${tornadoColor(risk.tornado_risk)}`}>
        Tornado: {risk.tornado_risk}
      </span>
      {risk.wetlands_percent > 0 && (
        <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-blue-50 text-blue-700">
          Wetlands: {risk.wetlands_percent.toFixed(0)}%
        </span>
      )}
      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
        risk.road_type === "paved" ? "bg-green-50 text-green-700" :
        risk.road_type === "unpaved" ? "bg-yellow-50 text-yellow-700" :
        "bg-red-50 text-red-700"
      }`}>
        Estrada: {risk.road_type === "paved" ? "Pavimentada" : risk.road_type === "unpaved" ? "Sem asfalto" : "Sem acesso"}
      </span>
    </div>
  );
}
