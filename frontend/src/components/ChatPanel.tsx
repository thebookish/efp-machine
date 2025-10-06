import { useEffect, useState, useRef } from "react";
import { askAI, getSlackDestinations } from "../lib/api";

type Suggestion = { id: string; name: string; type: "channel" | "user" | "whatsapp" };

export default function ChatPanel() {
  const [input, setInput] = useState("");
  const [log, setLog] = useState<{ role: "user" | "ai"; text: string }[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [allDestinations, setAllDestinations] = useState<Suggestion[]>([]);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [destMap, setDestMap] = useState<{ [name: string]: string }>({});
  const textRef = useRef<HTMLTextAreaElement>(null);

  // --- Fetch Slack + mock WhatsApp contacts ---
  useEffect(() => {
    getSlackDestinations().then((res) => {
      const slack = res.destinations || [];

      // ✅ Mock WhatsApp contacts
      const whatsapp = [
        { id: "+8801823564420", name: "Alice WhatsApp", type: "whatsapp" },
        { id: "+8801906786163", name: "Bob WhatsApp", type: "whatsapp" },
      ];

      const combined = [...slack, ...whatsapp];
      setAllDestinations(combined);

      // Map name → ID
      const map: any = {};
      combined.forEach((d: any) => {
        map[d.name] = d.id;
      });
      setDestMap(map);
    });
  }, []);

  // --- Auto expand textarea height ---
  useEffect(() => {
    if (textRef.current) {
      textRef.current.style.height = "auto";
      textRef.current.style.height = textRef.current.scrollHeight + "px";
    }
  }, [input]);

  // --- Autocomplete logic ---
  const onChangeInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setInput(value);

    if (value.toLowerCase().startsWith("send")) {
      const parts = value.split(" ");
      const last = parts[parts.length - 1].toLowerCase();
      const matches = allDestinations.filter((d) =>
        d.name.toLowerCase().includes(last)
      );
      setSuggestions(matches.slice(0, 5));
    } else {
      setSuggestions([]);
    }
  };

  const pickSuggestion = (s: Suggestion) => {
    const parts = input.split(" ");
    parts[parts.length - 1] = s.name;
    setInput(parts.join(" "));
    setSuggestions([]);
  };

  // --- Replace readable names with IDs ---
  const preprocessInput = (text: string) => {
    let replaced = text;
    Object.keys(destMap).forEach((name) => {
      if (replaced.includes(name)) replaced = replaced.replace(name, destMap[name]);
    });
    return replaced;
  };

  // --- Send message ---
  const send = async () => {
    if (!input.trim()) return;
    const userMsg = input.trim();
    setInput("");
    setSuggestions([]);
    setLog((l) => [...l, { role: "user", text: userMsg }]);

    try {
      const processed = preprocessInput(userMsg);
      const resp = await askAI(processed);
      if (resp.session_id && !sessionId) setSessionId(resp.session_id);

      const text = resp.detail || resp.reply || JSON.stringify(resp);
      setLog((l) => [...l, { role: "ai", text }]);
    } catch (e: any) {
      const msg =
        e?.response?.data?.detail || e?.message || "unknown error from backend";
      setLog((l) => [...l, { role: "ai", text: "Error: " + msg }]);
    }
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="p-4 bg-gray-900 shadow rounded-2xl h-full flex flex-col">
      <h2 className="text-xl font-bold mb-2 text-sky-400">AI Assistant</h2>

      {/* Chat log */}
      <div className="flex-1 overflow-y-auto space-y-3 mb-3 max-h-[400px] pr-1">
        {log.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-right" : "text-left"}>
            <span
              className={
                "inline-block px-3 py-2 rounded-2xl max-w-[80%] whitespace-pre-line break-words " +
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

      {/* Textarea input */}
      <div className="relative">
        <textarea
          ref={textRef}
          className="w-full border border-gray-700 bg-black text-gray-100 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-sky-500 resize-none overflow-hidden"
          rows={1}
          value={input}
          onChange={onChangeInput}
          onKeyDown={onKeyDown}
          placeholder="Type message... (Shift+Enter for new line, Enter to send)"
        />

        {suggestions.length > 0 && (
          <div className="absolute bottom-full mb-1 w-full bg-gray-800 border border-gray-700 rounded-lg shadow-lg z-10">
            {suggestions.map((s, i) => (
              <div
                key={i}
                className="px-3 py-2 hover:bg-gray-700 cursor-pointer flex justify-between"
                onClick={() => pickSuggestion(s)}
              >
                <span>{s.name}</span>
                <span className="text-xs text-gray-400">{s.type}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Send button */}
      <div className="mt-3">
        <button
          className="w-full py-2 rounded-xl bg-sky-500 hover:bg-sky-600 text-white font-medium"
          onClick={send}
        >
          Send
        </button>
      </div>
    </div>
  );
}
