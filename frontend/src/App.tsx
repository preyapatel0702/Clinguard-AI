import { BrowserRouter as Router, Routes, Route } from "react-router";
import { lazy, Suspense } from "react";
import AppLayout from "./layout/AppLayout";
import { ScrollToTop } from "./components/common/ScrollToTop";
import LoadingState from "./components/common/LoadingState";

// Route-based code splitting: each page ships as its own chunk so the
// initial bundle only contains the shell + whichever page loads first.
const Home = lazy(() => import("./pages/Dashboard/Home"));
const Audit = lazy(() => import("./pages/Audit/Audit"));
const Monitoring = lazy(() => import("./pages/Monitoring/Monitoring"));
const Pipeline = lazy(() => import("./pages/Pipeline/Pipeline"));
const Chat = lazy(() => import("./pages/Chat/Chat"));
const NotFound = lazy(() => import("./pages/OtherPage/NotFound"));

function RouteFallback() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <LoadingState label="Loading page…" heightClass="h-32" />
    </div>
  );
}

export default function App() {
  return (
    <Router>
      <ScrollToTop />
      <Suspense fallback={<RouteFallback />}>
        <Routes>
          {/* Dashboard Layout */}
          <Route element={<AppLayout />}>
            <Route index path="/" element={<Home />} />
            <Route path="/audit" element={<Audit />} />
            <Route path="/monitoring" element={<Monitoring />} />
            <Route path="/pipeline" element={<Pipeline />} />
            <Route path="/chat" element={<Chat />} />
          </Route>

          {/* Fallback Route */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Suspense>
    </Router>
  );
}
