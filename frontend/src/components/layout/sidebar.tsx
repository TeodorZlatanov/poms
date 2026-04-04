import { Link, useLocation } from "react-router";
import { ClipboardText, ChartBar } from "@phosphor-icons/react";
import type { Icon } from "@phosphor-icons/react";
import { cn } from "@/utils/cn";

const links: { to: string; label: string; icon: Icon }[] = [
  { to: "/", label: "Orders", icon: ClipboardText },
  { to: "/analytics", label: "Analytics", icon: ChartBar },
];

export function Sidebar() {
  const location = useLocation();

  return (
    <nav className="w-56 border-r border-border bg-surface p-3">
      <ul className="space-y-1">
        {links.map((link) => {
          const isActive =
            link.to === "/"
              ? location.pathname === "/" ||
                location.pathname.startsWith("/orders")
              : location.pathname.startsWith(link.to);

          const NavIcon = link.icon;

          return (
            <li key={link.to}>
              <Link
                to={link.to}
                className={cn(
                  "group flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-150",
                  isActive
                    ? "bg-primary/10 text-primary"
                    : "text-muted hover:bg-accent hover:text-foreground"
                )}
              >
                <NavIcon
                  size={20}
                  weight={isActive ? "fill" : "duotone"}
                  className="flex-shrink-0"
                />
                {link.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
