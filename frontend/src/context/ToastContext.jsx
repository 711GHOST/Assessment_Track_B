import { createContext, useCallback, useContext, useState } from "react";

const ToastContext = createContext(null);

let nextId = 0;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const dismiss = useCallback((id) => {
    setToasts((current) => current.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback(
    (message, type = "info") => {
      const id = ++nextId;
      setToasts((current) => [...current, { id, message, type }]);
      setTimeout(() => dismiss(id), 3800);
    },
    [dismiss]
  );

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="toast-stack">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`toast toast-${t.type}`}
            onClick={() => dismiss(t.id)}
          >
            <span className="toast-icon">
              {t.type === "success" ? "✓" : t.type === "error" ? "!" : "i"}
            </span>
            <span>{t.message}</span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext).toast;
}
