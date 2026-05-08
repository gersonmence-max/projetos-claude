import { Link, useLocation } from "react-router-dom";
import { LayoutDashboard, Activity, Map } from "lucide-react";
import { cn } from "../lib/utils";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/pipeline", label: "Pipeline", icon: Activity },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();

  return (
    <div className="flex min-h-screen" style={{ backgroundColor: "#0a0a0f" }}>
      {/* Sidebar */}
      <aside
        className="w-64 flex flex-col flex-shrink-0"
        style={{ backgroundColor: "#12121a", borderRight: "1px solid #1e1e2e" }}
      >
        {/* Logo */}
        <div className="p-6" style={{ borderBottom: "1px solid #1e1e2e" }}>
          <div className="flex items-center gap-3">
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center"
              style={{ backgroundColor: "#6c63ff" }}
            >
              <Map size={16} className="text-white" />
            </div>
            <div>
              <p className="text-sm font-semibold" style={{ color: "#e2e8f0" }}>
                Buscador de
              </p>
              <p className="text-xs" style={{ color: "#64748b" }}>
                Terrenos AL • AR
              </p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-4 space-y-1">
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => {
            const active = location.pathname === to;
            return (
              <Link
                key={to}
                to={to}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-150",
                  active ? "font-medium" : "hover:opacity-80"
                )}
                style={{
                  backgroundColor: active ? "rgba(108,99,255,0.1)" : "transparent",
                  color: active ? "#6c63ff" : "#64748b",
                }}
              >
                <Icon size={16} />
                {label}
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="p-4" style={{ borderTop: "1px solid #1e1e2e" }}>
          <p className="text-xs" style={{ color: "#64748b" }}>
            AL & AR Land Finder
          </p>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  );
}
