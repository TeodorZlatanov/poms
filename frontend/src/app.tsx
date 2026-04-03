import { BrowserRouter, Routes, Route } from "react-router";
import { DashboardPage } from "./pages/dashboard";
import { OrderPage } from "./pages/order";
import { AnalyticsPage } from "./pages/analytics";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route index element={<DashboardPage />} />
        <Route path="orders/:id" element={<OrderPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
      </Routes>
    </BrowserRouter>
  );
}
