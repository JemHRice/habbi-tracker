import "@fontsource-variable/fraunces";
import "@fontsource-variable/nunito-sans";
import "./styles/global.css";

import { PersistQueryClientProvider } from "@tanstack/react-query-persist-client";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import { App } from "./App";
import { AuthProvider } from "./auth/AuthContext";
import { persister, queryClient } from "./queryClient";

const container = document.getElementById("root");
if (!container) throw new Error("No #root element to mount into.");

createRoot(container).render(
  <StrictMode>
    <PersistQueryClientProvider
      client={queryClient}
      persistOptions={{
        persister,
        maxAge: 1000 * 60 * 60 * 24 * 3,
        // Never persist a mutation: nothing should be replayed on next open.
        dehydrateOptions: { shouldDehydrateMutation: () => false },
      }}
    >
      <AuthProvider>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </AuthProvider>
    </PersistQueryClientProvider>
  </StrictMode>,
);
