import { Routes, Route } from "react-router-dom";
import { ScenarioProvider } from "@/lib/scenario";
import { DashboardProvider } from "@/lib/dashboard";
import { AppShell } from "@/components/layout/AppShell";
import CommandCenter from "@/pages/CommandCenter";
import EventSimulation from "@/pages/EventSimulation";
import TrafficForecast from "@/pages/TrafficForecast";
import ResourcePlanner from "@/pages/ResourcePlanner";
import PostEventAnalytics from "@/pages/PostEventAnalytics";
import LiveMap from "@/pages/LiveMap";
import AlertsCenter from "@/pages/AlertsCenter";
import Reports from "@/pages/Reports";
import Settings from "@/pages/Settings";

export default function App() {
  return (
    <ScenarioProvider>
    <DashboardProvider>
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<CommandCenter />} />
        <Route path="/simulation" element={<EventSimulation />} />
        <Route path="/forecast" element={<TrafficForecast />} />
        <Route path="/resources" element={<ResourcePlanner />} />
        <Route path="/analytics" element={<PostEventAnalytics />} />
        <Route path="/map" element={<LiveMap />} />
        <Route path="/alerts" element={<AlertsCenter />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
    </Routes>
    </DashboardProvider>
    </ScenarioProvider>
  );
}
