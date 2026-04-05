import { PackageIcon } from "@phosphor-icons/react";
import { ThemeSwitcher } from "@/components/ui/themeSwitcher";

export function Header() {
  return (
    <header className="sticky top-0 z-40 border-b border-border bg-surface/95 backdrop-blur-sm">
      <div className="flex h-14 items-center justify-between px-6">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <PackageIcon size={18} weight="fill" className="text-primary-foreground" />
          </div>
          <div>
            <h1 className="text-sm font-semibold tracking-tight text-foreground">POMS</h1>
            <p className="text-[11px] leading-tight text-muted">Purchase Order Management</p>
          </div>
        </div>
        <ThemeSwitcher />
      </div>
    </header>
  );
}
