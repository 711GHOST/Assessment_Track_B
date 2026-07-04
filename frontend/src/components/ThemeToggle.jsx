import { useTheme } from "../context/ThemeContext";

export default function ThemeToggle() {
  const { theme, toggle } = useTheme();
  return (
    <button
      className="theme-toggle"
      onClick={toggle}
      title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
      aria-label="Toggle color theme"
    >
      <span className="theme-track">
        <span className="theme-thumb">{theme === "dark" ? "🌙" : "☀️"}</span>
      </span>
    </button>
  );
}
