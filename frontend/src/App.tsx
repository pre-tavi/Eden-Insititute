import { useState } from "react";
import { Route, Routes } from "react-router-dom";
import { Footer, Navbar } from "./components/ui";
import { AuthProvider, ProtectedRoute, useAuth } from "./context/AuthContext";
import { LoginPage, RegisterPage } from "./pages/AuthPages";
import { CatalogPage } from "./pages/CatalogPage";
import { CourseDetailPage } from "./pages/CourseDetailPage";
import { MyLearningPage } from "./pages/MyLearningPage";
import type { AudienceTier } from "./types/catalog";

function AppShell({
  audience,
  setAudience,
}: {
  audience: AudienceTier;
  setAudience: (audience: AudienceTier) => void;
}) {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen flex flex-col bg-[var(--color-bg-canvas)] text-[var(--color-text-primary)]">
      <Navbar
        audience={audience}
        onAudienceChange={setAudience}
        user={user}
        onLogout={logout}
      />

      <main className="flex-1">
        <Routes>
          <Route path="/" element={<CatalogPage audience={audience} />} />
          <Route
            path="/courses/:slug"
            element={<CourseDetailPage audience={audience} />}
          />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route
            path="/my-learning"
            element={
              <ProtectedRoute>
                <MyLearningPage />
              </ProtectedRoute>
            }
          />
        </Routes>
      </main>

      <Footer />
    </div>
  );
}

export default function App() {
  const [audience, setAudience] = useState<AudienceTier>("local");

  return (
    <AuthProvider onAudienceSync={setAudience}>
      <AppShell audience={audience} setAudience={setAudience} />
    </AuthProvider>
  );
}