import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import PropertyDetail from "./pages/PropertyDetail";
import Pipeline from "./pages/Pipeline";

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/property/:id" element={<PropertyDetail />} />
          <Route path="/pipeline" element={<Pipeline />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
