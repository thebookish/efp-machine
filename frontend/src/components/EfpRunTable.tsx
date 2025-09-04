import { useEffect, useState } from "react";

type RunRow = {
  index_name: string;
  bid: number | null;
  offer: number | null;
  cash_ref: number | null;
  watchpoint: boolean;
  expiry: {
    index: string;
    status: string;
    expiry_date: string | null;
  };
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
  const [copiedRun, setCopiedRun] = useState(false);
  const [copiedRecaps, setCopiedRecaps] = useState(false);

  useEffect(() => {
    // --- 1. Load the latest snapshot immediately (REST fetch) ---
    const fetchLatest = async () => {
      try {
        const res = await fetch("https://efp-machine-2.onrender.com/api/efp/run");
        if (res.ok) {
          const data: RunRow[] = await res.json();
          setRunRows(data);
        }
      } catch (err) {
        console.error("Failed to fetch EFP run:", err);
      }
    };
    fetchLatest();

     // --- Connect Run WebSocket ---
  let runSocket: WebSocket;
  const connectRun = () => {
    runSocket = new WebSocket(`wss://efp-machine-2.onrender.com/api/efp/ws/run`);
    runSocket.onmessage = (e) => {
      const payload: Payload = JSON.parse(e.data);
      setRunRows(payload.run);
      setRecaps(payload.recaps); // you already broadcast recaps in run
    };
    runSocket.onerror = () => console.warn("Run WebSocket error");
    runSocket.onclose = () => setTimeout(connectRun, 2000);
  };
  connectRun();

  // --- Connect Recap WebSocket (optional if you want live recaps separate) ---
  let recapSocket: WebSocket;
  const connectRecaps = () => {
    recapSocket = new WebSocket(`wss://efp-machine-2.onrender.com/api/efp/ws/recaps`);
    recapSocket.onmessage = (e) => {
      const data: Recap[] = JSON.parse(e.data);
      setRecaps(data);
    };
    recapSocket.onerror = () => console.warn("Recaps WebSocket error");
    recapSocket.onclose = () => setTimeout(connectRecaps, 2000);
  };
  connectRecaps();

  return () => {
    runSocket && runSocket.close();
    recapSocket && recapSocket.close();
  };
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
      setCopiedRun(true);
      setTimeout(() => setCopiedRun(false), 2000);
    } catch (err) {
      console.error("Failed to copy run:", err);
    }
  };

  const copyRecaps = async () => {
    if (recaps.length === 0) return;

    const header = "Trade Recaps";
    const rows = recaps
      .map(
        (r) =>
          `${r.index_name} → ${r.recap_text} (${new Date(
            r.created_at
          ).toLocaleTimeString()})`
      )
      .join("\n");

    const text = `${header}\n${rows}`;

    try {
      await navigator.clipboard.writeText(text);
      setCopiedRecaps(true);
      setTimeout(() => setCopiedRecaps(false), 2000);
    } catch (err) {
      console.error("Failed to copy recaps:", err);
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
          {copiedRun ? "Copied!" : "Copy Run"}
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
             <th className="text-left p-2">Watchpoint</th>
             <th className="text-left p-2">Expiry</th>
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
<td className="p-2">
        {r.watchpoint ? (
          <span className="text-red-500 font-bold">⚠</span>
        ) : (
          "-"
        )}
      </td>
  <td className="p-2">
    {r.expiry.status === "Expired" && (
      <span className="text-red-500 font-semibold">Expired ({r.expiry.expiry_date})</span>
    )}
    {r.expiry.status === "In expiry window" && (
      <span className="text-yellow-400 font-semibold">In window ({r.expiry.expiry_date})</span>
    )}
    {r.expiry.status === "Pending" && (
      <span className="text-green-400 font-semibold">Pending ({r.expiry.expiry_date})</span>
    )}
  </td>

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
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-sky-400 mb-2">
            Trade Recaps
          </h3>
          <button
            onClick={copyRecaps}
            className="px-3 py-1 text-sm bg-sky-600 hover:bg-sky-700 rounded-lg text-white"
          >
            {copiedRecaps ? "Copied!" : "Copy Recaps"}
          </button>
        </div>
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
