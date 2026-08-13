import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { SWRConfig } from "swr";
import App from "./App";
import "./i18n";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <SWRConfig
      value={{
        keepPreviousData: true,
        revalidateOnFocus: false,
        dedupingInterval: 8000,
      }}
    >
      <App />
    </SWRConfig>
  </StrictMode>,
);
