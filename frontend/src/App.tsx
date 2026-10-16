import { useState } from "react";
import { Route, Routes } from "react-router-dom";
import { Footer, Navbar } from "./components/ui";
import { CatalogPage } from "./pages/CatalogPage";
import { CourseDetailPage } from "./pages/CourseDetailPage";
import type { AudienceTier } from "./types/catalog";

function AuthPlaceholderPage() {
  return (
    <section className="mx-auto max-w-md px-4 py-12">
      <div className="rounded-[var(--radius-md)] border border-[var(--color-border-hairline)] bg-[var(--color-bg-surface)] p-6 shadow-[var(--shadow-card)]">
        <p className="font-clinical-mono text-xs font-semibold uppercase tracking-wider text-[var(--color-accent-terracotta)]">
          Phase 2 · Student Access Gate
        </p>
        <h1 className="mt-1 font-editorial text-2xl font-semibold text-[var(--color-text-primary)]">
          Student Portal Sign In
        </h1>
        <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
          Protected by server-side Django session authentication, Argon2id password hashing, and
          HttpOnly + SameSite=Lax cookies.
        </p>
      </div>
    </section>
  );
}

function MyLearningPlaceholderPage() {
  return (
    <section className="mx-auto max-w-5xl px-4 py-12">
      <div className="rounded-[var(--radius-md)] border border-[var(--color-border-hairline)] bg-[var(--color-bg-surface)] p-6 shadow-[var(--shadow-card)]">
        <p className="font-clinical-mono text-xs font-semibold uppercase tracking-wider text-[var(--color-accent-terracotta)]">
          Student Classroom Shell
        </p>
        <h1 className="mt-1 font-editorial text-2xl font-semibold text-[var(--color-text-primary)]">
          My Learning Dashboard
        </h1>
        <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
          View active cohort enrollments, resume signed video lessons, join live Google Meet
          lectures in your local timezone, and book 5-day Nairobi or Embu residency blocks.
        </p>
      </div>
    </section>
  );
}

export default function App() {
  const [audience, setAudience] = useState<AudienceTier>("local");

  return (
    <div className="min-h-screen flex flex-col bg-[var(--color-bg-canvas)] text-[var(--color-text-primary)]">
      <Navbar audience={audience} onAudienceChange={setAudience} />

      <main className="flex-1">
        <Routes>
          <Route path="/" element={<CatalogPage audience={audience} />} />
          <Route
            path="/courses/:slug"
            element={<CourseDetailPage audience={audience} />}
          />
          <Route path="/login" element={<AuthPlaceholderPage />} />
          <Route path="/register" element={<AuthPlaceholderPage />} />
          <Route path="/my-learning" element={<MyLearningPlaceholderPage />} />
        </Routes>
      </main>

      <Footer />
    </div>
  );
}