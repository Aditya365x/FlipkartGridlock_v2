import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { useDashboard } from "@/lib/dashboard";

export function AppShell() {
  // shared dashboard source — banner stays in sync with the Command Center (no duplicate fetch)
  const { data } = useDashboard();
  const critical = data?.alerts.find((a) => a.type === "error") ?? null;

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar criticalAlert={critical} notifications={data?.alerts.length ?? 0} />
        <main className="flex-1 overflow-y-auto p-5">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
