import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./App.css";
import WestpacCSDashboard from "./App.tsx";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <WestpacCSDashboard />
  </StrictMode>
);
