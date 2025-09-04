import { useState } from "react";
import { askAI } from "../lib/api";

export default function ChatPanel() {
  const [input, setInput] = useState("");
  const [log, setLog] = useState<{ role: "user" | "ai"; text: string }[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);

  const send = async () => {
    if (!input.trim()) return;
    const user = input;
    setInput("");
    setLog((l) => [...l, { role: "user", text: user }]);

    try {
      const resp = await askAI(user, sessionId || undefined);

      // save sessionId if backend generated one
      if (resp.session_id && !sessionId) {
        setSessionId(resp.session_id);
      }

      const text = resp.detail || resp.reply || JSON.stringify(resp);
      setLog((l) => [...l, { role: "ai", text }]);
    } catch (e: any) {
      const msg =
        e?.response?.data?.detail || e?.message || "unknown error from backend";
      setLog((l) => [...l, { role: "ai", text: "Error: " + msg }]);
    }
  };

  const onKey = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") send();
  };

  return (
    <div className="p-4 bg-gray-900 shadow rounded-2xl h-full flex flex-col">
      <h2 className="text-xl font-bold mb-2 text-sky-400">AI Assistant</h2>

      {/* Scrollable chat log */}
      <div className="flex-1 overflow-y-auto space-y-2 mb-3 max-h-[400px] pr-1">
        {log.map((m, i) => (
          <div
            key={i}
            className={m.role === "user" ? "text-right" : "text-left"}
          >
            <span
              className={
                "inline-block px-3 py-2 rounded-2xl max-w-[80%] break-words " +
                (m.role === "user"
                  ? "bg-sky-600 text-white"
                  : "bg-gray-700 text-gray-100")
              }
            >
              {m.text}
            </span>
          </div>
        ))}
      </div>

      {/* Input + send button */}
      <div className="flex gap-2">
        <input
          className="flex-1 border border-gray-700 bg-black text-gray-100 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-sky-500"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKey}
          placeholder="e.g., Update SX5E bid to -3.25 (cash ref 4210.5)"
        />
        <button
          className="px-4 py-2 rounded-xl bg-sky-500 hover:bg-sky-600 text-white font-medium"
          onClick={send}
        >
          Send
        </button>
      </div>
    </div>
  );
}
