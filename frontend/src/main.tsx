import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { ChatProvider } from "./state/chat";
import { SettingsProvider } from "./state/settings";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <SettingsProvider>
      <ChatProvider>
        <App />
      </ChatProvider>
    </SettingsProvider>
  </StrictMode>,
);
