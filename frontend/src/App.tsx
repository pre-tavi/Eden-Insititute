import { Link, Route, Routes } from "react-router-dom";

function CatalogShell() {
  return (
    <section className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="text-3xl font-bold tracking-tight text-slate-900">
        Dr. Violet&apos;s Psychology Programmes
      </h1>
      <p className="mt-2 text-slate-600">
        Certificate and Diploma courses with live lectures and optional 5-day practical
        residency blocks in Nairobi and Embu.
      </p>
    </section>
  );
}

function CourseDetailShell() {
  return (
    <section className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="text-2xl font-semibold text-slate-900">Course Detail</h1>
      <p className="mt-2 text-slate-600">
        Course outline, local (KES) and international (USD) pricing, and residency details.
      </p>
    </section>
  );
}

function AuthShell() {
  return (
    <section className="mx-auto max-w-md px-4 py-10">
      <h1 className="text-2xl font-semibold text-slate-900">Student Portal Access</h1>
      <p className="mt-2 text-slate-600">
        Protected by server-side Django session authentication and CSRF cookies.
      </p>
    </section>
  );
}

function MyLearningShell() {
  return (
    <section className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="text-2xl font-semibold text-slate-900">My Learning</h1>
      <p className="mt-2 text-slate-600">
        Track lesson progress, join live Google Meet lectures, and manage residency bookings.
      </p>
    </section>
  );
}

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-slate-200 bg-white">
        <nav
          aria-label="Primary Navigation"
          className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4"
        >
          <Link to="/" className="text-lg font-bold text-slate-900">
            EdenLMS
          </Link>
          <div className="flex items-center gap-6 text-sm font-medium text-slate-700">
            <Link to="/" className="hover:text-slate-950">
              Catalog
            </Link>
            <Link to="/my-learning" className="hover:text-slate-950">
              My Learning
            </Link>
            <Link to="/login" className="hover:text-slate-950">
              Sign In
            </Link>
          </div>
        </nav>
      </header>

      <main className="flex-1">
        <Routes>
          <Route path="/" element={<CatalogShell />} />
          <Route path="/courses/:slug" element={<CourseDetailShell />} />
          <Route path="/login" element={<AuthShell />} />
          <Route path="/register" element={<AuthShell />} />
          <Route path="/my-learning" element={<MyLearningShell />} />
        </Routes>
      </main>
    </div>
  );
}