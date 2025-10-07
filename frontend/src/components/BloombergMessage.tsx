import axios from "axios";
import { useEffect, useState } from "react";

interface BloombergMessage {
  eventId: string;
  originalMessage: string;
  messageStatus: string;
  current_json?: any;
  original_llm_json?: any;
  created_at?: string;
}
export const api = axios.create({
  baseURL: "https://efp-machine-2.onrender.com/api",
  timeout: 10000,
});
export default function BloombergMessagesPanel() {
  const [messages, setMessages] = useState<BloombergMessage[]>([]);
  const [selected, setSelected] = useState<BloombergMessage | null>(null);
  const [llmResponse, setLlmResponse] = useState<string>("");

  // WebSocket setup
  useEffect(() => {
    const wsUrl = `wss://efp-machine-2.onrender.com/api/messages/ws`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => console.log("🌐 Connected to Bloomberg WS");
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log("📩 WS Message:", data);

      if (data.type === "messages_list") {
        setMessages(data.payload);
      } else if (data.type === "message_new") {
        setMessages((prev) => [data.payload, ...prev]);
      } else if (data.type === "message_update") {
        setMessages((prev) =>
          prev.map((m) => (m.eventId === data.payload.eventId ? data.payload : m))
        );
      }
    };

    ws.onclose = () => console.log("❌ WS closed");
    ws.onerror = (err) => console.error("⚠️ WS error", err);

    return () => ws.close();
  }, []);

  // --- Handle LLM response update ---
  const sendLlmResponse = async () => {
    if (!selected || !llmResponse.trim()) return alert("Select a message first.");

    try {
      const parsed = JSON.parse(llmResponse);
      const res = await api.put(`/messages/set-llm-response/${selected.eventId}`, parsed);
      alert(`✅ LLM response saved for ${selected.eventId}`);
      setLlmResponse("");
      setSelected(null);
    } catch (e: any) {
      console.error(e);
      alert("❌ Failed to send LLM response. Make sure JSON is valid.");
    }
  };

  return (
    <div className="p-4 bg-gray-900 text-gray-100 rounded-2xl h-full flex flex-col">
      <h2 className="text-xl font-bold mb-4 text-sky-400">Bloomberg Messages</h2>

      <div className="flex gap-4 h-full">
        {/* === Message List === */}
        <div className="flex-1 border border-gray-700 rounded-xl p-3 overflow-y-auto max-h-[500px]">
          {messages.length === 0 && (
            <p className="text-gray-500">No messages yet...</p>
          )}

          {messages.map((m) => (
            <div
              key={m.eventId}
              onClick={() => setSelected(m)}
              className={`p-2 rounded-lg mb-2 cursor-pointer ${
                selected?.eventId === m.eventId
                  ? "bg-sky-700 text-white"
                  : "bg-gray-800 hover:bg-gray-700"
              }`}
            >
              <div className="text-sm text-gray-400">
                {new Date(m.created_at || "").toLocaleString()}
              </div>
              <div className="font-medium text-base">{m.originalMessage}</div>
              <div className="text-xs text-gray-400 italic">
                Status: {m.messageStatus}
              </div>
            </div>
          ))}
        </div>

        {/* === LLM Response Editor === */}
        <div className="w-1/2 border border-gray-700 rounded-xl p-3 flex flex-col">
          <h3 className="font-semibold text-lg mb-2 text-sky-300">
            Attach LLM Response
          </h3>

          {selected ? (
            <>
              <div className="text-sm mb-1 text-gray-400">
                For Message: <b>{selected.eventId}</b>
              </div>
              <div className="text-xs mb-3 text-gray-500">
                Original: {selected.originalMessage}
              </div>
            </>
          ) : (
            <p className="text-gray-500 text-sm mb-2">
              Select a message from the left to attach a response.
            </p>
          )}

          <textarea
            className="flex-1 w-full p-2 rounded-lg bg-black border border-gray-700 text-gray-100 text-sm font-mono"
            value={llmResponse}
            onChange={(e) => setLlmResponse(e.target.value)}
            placeholder={`{\n  "instrument": "SX5E",\n  "strategy": "TRF",\n  "basis": 3.75,\n  "other": [...] \n}`}
          />

          <button
            onClick={sendLlmResponse}
            className="mt-3 py-2 px-3 rounded-xl bg-sky-500 hover:bg-sky-600 text-white font-medium"
          >
            Save LLM Response
          </button>
        </div>
      </div>
    </div>
  );
}
