import { BrowserRouter, Routes, Route } from "react-router";
import { Layout } from "./components/layout/layout";
import { DashboardPage } from "./pages/dashboard";
import { OrderPage } from "./pages/order";
import { AnalyticsPage } from "./pages/analytics";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<DashboardPage />} />
          <Route path="orders/:id" element={<OrderPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
