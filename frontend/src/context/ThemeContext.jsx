import { createContext, useContext, useEffect, useState } from "react";

const ThemeContext = createContext(null);
const STORAGE_KEY = "rag.theme";

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(
    () => localStorage.getItem(STORAGE_KEY) || "dark"
  );

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem(STORAGE_KEY, theme);
  }, [theme]);

  const toggle = () => setTheme((t) => (t === "dark" ? "light" : "dark"));

  return (
    <ThemeContext.Provider value={{ theme, toggle }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}
