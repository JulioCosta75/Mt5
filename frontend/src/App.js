import React, { useEffect, useState } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Dashboard from "@/Dashboard";
import About from "@/pages/About";
import Documentation from "@/pages/Documentation";
import BrandBoot from "@/components/BrandBoot";

function App() {
  const [booting, setBooting] = useState(() => {
    // Show the welcome/loading splash once per browser session.
    // `?noboot=1` skips it (useful for testing / deep links).
    try {
      if (new URLSearchParams(window.location.search).get("noboot")) return false;
      return !sessionStorage.getItem("ffl_booted");
    } catch {
      return true;
    }
  });

  useEffect(() => {
    if (!booting) return;
    try {
      sessionStorage.setItem("ffl_booted", "1");
    } catch {
      /* ignore */
    }
  }, [booting]);

  return (
    <div className="App">
      {booting && <BrandBoot onDone={() => setBooting(false)} />}
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/about" element={<About />} />
          <Route path="/docs" element={<Documentation />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
