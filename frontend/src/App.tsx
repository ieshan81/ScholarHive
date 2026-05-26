import { Routes, Route } from "react-router-dom";
import { Layout } from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Radar from "./pages/Radar";
import Queue from "./pages/Queue";
import Essays from "./pages/Essays";
import Profile from "./pages/Profile";
import Stories from "./pages/Stories";
import Gmail from "./pages/Gmail";
import Telegram from "./pages/Telegram";
import Documents from "./pages/Documents";
import SettingsPage from "./pages/Settings";
import WebSearch from "./pages/WebSearch";
import Portals from "./pages/Portals";
import ProfileGraph from "./pages/ProfileGraph";
import MemoryVault from "./pages/MemoryVault";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/radar" element={<Radar />} />
        <Route path="/web-search" element={<WebSearch />} />
        <Route path="/queue" element={<Queue />} />
        <Route path="/essays" element={<Essays />} />
        <Route path="/memory-vault" element={<MemoryVault />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/stories" element={<Stories />} />
        <Route path="/gmail" element={<Gmail />} />
        <Route path="/telegram" element={<Telegram />} />
        <Route path="/documents" element={<Documents />} />
        <Route path="/trusted-platforms" element={<Portals />} />
        <Route path="/portals" element={<Portals />} />
        <Route path="/profile-graph" element={<ProfileGraph />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
