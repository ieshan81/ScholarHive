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

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/radar" element={<Radar />} />
        <Route path="/queue" element={<Queue />} />
        <Route path="/essays" element={<Essays />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/stories" element={<Stories />} />
        <Route path="/gmail" element={<Gmail />} />
        <Route path="/telegram" element={<Telegram />} />
        <Route path="/documents" element={<Documents />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
