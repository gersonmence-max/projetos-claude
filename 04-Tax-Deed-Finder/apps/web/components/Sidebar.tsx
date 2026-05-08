"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  MapPin,
  Star,
  BarChart2,
  Settings,
  Clock,
} from "lucide-react";

const nav = [
  { href: "/",              label: "Dashboard",    Icon: LayoutDashboard },
  { href: "/imoveis",       label: "Imóveis",      Icon: MapPin },
  { href: "/salvos",        label: "Salvos",        Icon: Star },
  { href: "/analytics",     label: "Analytics",    Icon: BarChart2 },
  { href: "/configuracoes", label: "Configurações", Icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-bg-sidebar border-r border-[rgba(201,145,10,0.30)] flex flex-col overflow-hidden">
      {/* Topographic SVG background */}
      <svg
        className="absolute inset-0 w-full h-full pointer-events-none opacity-[0.04]"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <pattern id="topo" x="0" y="0" width="80" height="80" patternUnits="userSpaceOnUse">
            <path d="M0 40 Q20 20 40 40 Q60 60 80 40" fill="none" stroke="#f0b429" strokeWidth="1"/>
            <path d="M0 60 Q20 40 40 60 Q60 80 80 60" fill="none" stroke="#f0b429" strokeWidth="1"/>
            <path d="M0 20 Q20 0 40 20 Q60 40 80 20" fill="none" stroke="#f0b429" strokeWidth="1"/>
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#topo)" />
      </svg>

      {/* Logo */}
      <div className="relative z-10 p-6 border-b border-[rgba(201,145,10,0.30)]">
        <h1 className="font-cinzel text-xl font-bold text-gold-bright">LandHQ</h1>
        <p className="text-[10px] tracking-widest uppercase text-parchment-dim mt-0.5">
          Monitor de Tax Deed
        </p>
      </div>

      {/* Nav */}
      <nav className="relative z-10 flex-1 p-4 space-y-0.5">
        {nav.map(({ href, label, Icon }) => {
          const active = pathname === href || (href !== "/" && pathname.startsWith(href));
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2.5 text-sm transition-all duration-150 ${
                active
                  ? "text-gold-bright bg-gold/15 border-l-2 border-gold-bright"
                  : "text-parchment-muted hover:text-gold-bright hover:bg-gold/5 hover:border-l-2 hover:border-gold-bright border-l-2 border-transparent"
              }`}
            >
              <Icon size={16} strokeWidth={1.5} />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="relative z-10 p-4 border-t border-[rgba(201,145,10,0.30)]">
        <div className="flex items-center gap-2">
          <Clock size={12} strokeWidth={1.5} className="text-parchment-dim" />
          <p className="text-[11px] text-parchment-dim">Coleta diária às 2h</p>
        </div>
      </div>
    </aside>
  );
}
