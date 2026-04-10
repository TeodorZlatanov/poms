import { Outlet } from "react-router";
import { Header } from "@/components/layout/header";
import { Sidebar } from "@/components/layout/sidebar";

export function Layout() {
  return (
    <div className="flex h-screen flex-col bg-surface-alt">
      <Header />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
