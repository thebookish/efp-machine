import { useEffect, useState } from "react";

type RunRow = {
  index_name: string;
  bid: number | null;
  offer: number | null;
  cash_ref: number | null;
};

type Recap = {
  index_name: string;
  price: number;
  lots: number;
  cash_ref: number;
  recap_text: string;
  created_at: string;
};

type Payload = {
  run: RunRow[];
  recaps: Recap[];
};

export default function EfpRunTable() {
  const [runRows, setRunRows] = useState<RunRow[]>([]);
  const [recaps, setRecaps] = useState<Recap[]>([]);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    // --- 1. Load the latest snapshot immediately (REST fetch) ---
    const fetchLatest = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/efp/run");
        if (res.ok) {
          const data: RunRow[] = await res.json();
          setRunRows(data);
        }
      } catch (err) {
        console.error("Failed to fetch EFP run:", err);
      }
    };
    fetchLatest();

    // --- 2. Connect WebSocket for live updates ---
    let ws: WebSocket;
    const connect = () => {
      ws = new WebSocket(`ws://localhost:8000/api/efp/ws/run`);
      ws.onmessage = (e) => {
        const payload: Payload = JSON.parse(e.data);
        setRunRows(payload.run);
        setRecaps(payload.recaps);
      };
      ws.onerror = () => {
        console.warn("WebSocket error");
      };
      ws.onclose = () => {
        console.log("WebSocket closed, reconnecting...");
        setTimeout(connect, 2000);
      };
    };

    connect();
    return () => ws && ws.close();
  }, []);

  const copyRun = async () => {
    if (runRows.length === 0) return;

    const header = "EFP’s\nEFP's          Price          Cash Ref";
    const rows = runRows
      .map(
        (r) =>
          `${r.index_name} EFP   ${(r.bid ?? "-")}/${r.offer ?? "-"}   ${
            r.cash_ref ?? "-"
          }`
      )
      .join("\n");

    const text = `${header}\n${rows}`;

    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  return (
    <div className="p-4 bg-gray-900 shadow rounded-2xl">
      {/* --- Run Table --- */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold mb-2 text-sky-400">EFP’s</h2>
        <button
          onClick={copyRun}
          className="px-3 py-1 text-sm bg-sky-600 hover:bg-sky-700 rounded-lg text-white"
        >
          {copied ? "Copied!" : "Copy Run"}
        </button>
      </div>
      <div className="text-xs text-gray-400 mb-2">
        Columns: EFP’s | Price | Cash Ref
      </div>

      <table className="w-full text-sm text-gray-200">
        <thead className="border-b border-gray-700">
          <tr>
            <th className="text-left p-2">EFP’s</th>
            <th className="text-left p-2">Price</th>
            <th className="text-left p-2">Cash Ref</th>
          </tr>
        </thead>
        <tbody>
          {runRows.map((r, i) => (
            <tr key={i} className="border-b border-gray-700">
              <td className="p-2">{r.index_name + " EFP"}</td>
              <td className="p-2">
                {(r.bid ?? "-") + " / " + (r.offer ?? "-")}
              </td>
              <td className="p-2">{r.cash_ref ?? "-"}</td>
            </tr>
          ))}
          {runRows.length === 0 && (
            <tr>
              <td colSpan={3} className="p-3 text-center text-gray-500">
                No rows yet — waiting for latest EFP run.
              </td>
            </tr>
          )}
        </tbody>
      </table>

      {/* --- Inline Recaps --- */}
      <div className="mt-4">
        <h3 className="text-lg font-semibold text-sky-400 mb-2">Trade Recaps</h3>
        {recaps.length === 0 ? (
          <div className="text-gray-500 text-sm">No trades yet.</div>
        ) : (
          <ul className="space-y-1 text-sm text-gray-200">
            {recaps.map((r, i) => (
              <li key={i} className="border-b border-gray-700 pb-1">
                <span className="font-medium">{r.index_name}</span> →{" "}
                {r.recap_text}{" "}
                <span className="text-xs text-gray-400">
                  ({new Date(r.created_at).toLocaleTimeString()})
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
