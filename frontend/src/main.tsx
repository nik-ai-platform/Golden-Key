import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";

import { AuthProvider } from "./auth/AuthContext";
import { AppRouter } from "./routes/AppRouter";
import { ThemeModeProvider } from "./theme/ThemeModeProvider";

const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ThemeModeProvider>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AuthProvider>
            <AppRouter />
          </AuthProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeModeProvider>
  </React.StrictMode>,
);
