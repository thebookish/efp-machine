import { useEffect, useState } from "react";
import { askAI, getSlackDestinations } from "../lib/api";

type Suggestion = { id: string; name: string; type: "channel" | "user" | "whatsapp" };

export default function ChatPanel() {
  const [input, setInput] = useState("");
  const [log, setLog] = useState<{ role: "user" | "ai"; text: string }[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [allDestinations, setAllDestinations] = useState<Suggestion[]>([]);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [destMap, setDestMap] = useState<{ [name: string]: string }>({});

  // --- Fetch Slack + add mock WhatsApp contacts ---
  useEffect(() => {
    getSlackDestinations().then((res) => {
      const slack = res.destinations || [];

      // ✅ Mock WhatsApp contacts (replace with DB later)
      const whatsapp = [
        { id: "+8801823564420", name: "Alice WhatsApp", type: "whatsapp" },
        { id: "+8801906786163", name: "Bob WhatsApp", type: "whatsapp" },
      ];

      const combined = [...slack, ...whatsapp];
      setAllDestinations(combined);

      // Build name → id map for replacement
      const map: any = {};
      combined.forEach((d: any) => { map[d.name] = d.id });
      setDestMap(map);
    });
  }, []);

  // --- Handle input ---
  const onChangeInput = (e: React.ChangeEvent<HTMLInputElement>) => {
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
    parts[parts.length - 1] = s.name; // show readable name
    setInput(parts.join(" "));
    setSuggestions([]);
  };

  // --- Replace names with IDs before sending ---
  const preprocessInput = (text: string) => {
    let replaced = text;
    Object.keys(destMap).forEach((name) => {
      if (replaced.includes(name)) {
        replaced = replaced.replace(name, destMap[name]);
      }
    });
    return replaced;
  };

  const send = async () => {
    if (!input.trim()) return;
    const userMsg = input;
    setInput("");
    setSuggestions([]);
    setLog((l) => [...l, { role: "user", text: userMsg }]);

    try {
      // 👇 Replace names with Slack/WhatsApp IDs
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

  const onKey = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") send();
  };

  return (
    <div className="p-4 bg-gray-900 shadow rounded-2xl h-full flex flex-col">
      <h2 className="text-xl font-bold mb-2 text-sky-400">AI Assistant</h2>

      {/* Chat log */}
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

      {/* Input with autocomplete */}
      <div className="relative">
        <input
          className="w-full border border-gray-700 bg-black text-gray-100 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-sky-500"
          value={input}
          onChange={onChangeInput}
          onKeyDown={onKey}
          placeholder="e.g., send hello to Alice WhatsApp"
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

      <div className="mt-2">
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
