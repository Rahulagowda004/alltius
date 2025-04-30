import React from "react";
import { ThemeProvider } from "styled-components";
import { lightTheme, darkTheme } from "./styles/theme";
import { useTheme } from "./hooks/useTheme";
import Header from "./components/Header/Header";
import ChatBot from "./components/ChatBot/ChatBot";
import "./styles/global.css";

const App: React.FC = () => {
  const { theme, toggleTheme } = useTheme();

  return (
    <ThemeProvider theme={theme === "light" ? lightTheme : darkTheme}>
      <div
        className="app-container"
        style={{
          backgroundColor:
            theme === "light" ? lightTheme.background : darkTheme.background,
          color: theme === "light" ? lightTheme.text : darkTheme.text,
        }}
      >
        <Header theme={theme} toggleTheme={toggleTheme} />
        <div className="chatbot-container">
          <ChatBot />
        </div>
      </div>
    </ThemeProvider>
  );
};

export default App;
