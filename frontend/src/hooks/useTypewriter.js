import { useEffect, useRef, useState } from "react";

// Reveals `text` word-by-word for a lightweight "streaming" feel on fresh
// answers. When `enabled` is false (e.g. history), the full text shows
// instantly.
export function useTypewriter(text, enabled) {
  const [output, setOutput] = useState(enabled ? "" : text);
  const [done, setDone] = useState(!enabled);
  const timer = useRef(null);

  useEffect(() => {
    if (!enabled) {
      setOutput(text);
      setDone(true);
      return;
    }
    const words = text.split(" ");
    let i = 0;
    setOutput("");
    setDone(false);
    timer.current = setInterval(() => {
      i += 1;
      setOutput(words.slice(0, i).join(" "));
      if (i >= words.length) {
        clearInterval(timer.current);
        setDone(true);
      }
    }, 28);
    return () => clearInterval(timer.current);
  }, [text, enabled]);

  return { output, done };
}
