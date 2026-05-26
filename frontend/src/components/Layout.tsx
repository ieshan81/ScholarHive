import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard,
  Radar,
  Globe,
  Kanban,
  PenLine,
  Brain,
  Globe2,
  Mail,
  MessageCircle,
  Settings,
} from "lucide-react";

const nav = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/radar", label: "Scholarship Radar", icon: Radar },
  { to: "/web-search", label: "Web Search", icon: Globe },
  { to: "/gmail", label: "Gmail Scanner", icon: Mail },
  { to: "/portals", label: "Portal Registry", icon: Globe2 },
  { to: "/memory-vault", label: "Memory Vault", icon: Brain },
  { to: "/queue", label: "Application Queue", icon: Kanban },
  { to: "/essays", label: "Essay Studio", icon: PenLine },
  { to: "/telegram", label: "Telegram", icon: MessageCircle },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function Layout() {
  return (
    <div className="flex min-h-screen">
      <aside className="w-64 border-r border-hive-border bg-hive-panel/80 backdrop-blur p-4 flex flex-col">
        <div className="mb-8 px-2">
          <h1 className="font-display text-xl text-hive-gold tracking-wide">ScholarHive AI</h1>
          <p className="text-xs text-hive-muted mt-1">Private Scholarship OS</p>
        </div>
        <nav className="flex-1 space-y-1">
          {nav.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition ${
                  isActive
                    ? "bg-hive-gold/15 text-hive-gold border border-hive-gold/30"
                    : "text-slate-300 hover:bg-hive-card"
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>
        <p className="text-[10px] text-hive-muted px-2 mt-4">
          Legacy routes (/profile, /stories, /documents) still work — use Memory Vault
        </p>
      </aside>
      <main className="flex-1 p-8 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
