import { Link, Navigate, Route, Routes } from "react-router-dom";
import DemoConsole from "./screens/DemoConsole";
import AlertPage from "./screens/AlertPage";
import NightOps from "./screens/NightOps";
import PilotResults from "./screens/PilotResults";
import DriverSetup from "./screens/DriverSetup";
import ParkedHome from "./screens/ParkedHome";

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/demo" replace />} />
      <Route path="/demo" element={<DemoConsole />} />
      <Route path="/a/:token" element={<AlertPage />} />
      <Route path="/ops" element={<NightOps />} />
      <Route path="/pilot" element={<PilotResults />} />
      <Route path="/setup" element={<DriverSetup />} />
      <Route path="/home" element={<ParkedHome />} />
      <Route
        path="*"
        element={
          <div className="flex min-h-screen flex-col items-center justify-center gap-2 bg-night text-ink">
            <p className="text-lg font-medium">Page not found</p>
            <Link to="/demo" className="underline">
              Back to demo console
            </Link>
          </div>
        }
      />
    </Routes>
  );
}
