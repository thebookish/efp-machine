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

  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/api/efp/ws/run`);
    ws.onmessage = (e) => {
      const payload: Payload = JSON.parse(e.data);
      setRunRows(payload.run);
      setRecaps(payload.recaps);
    };
    ws.onerror = () => { /* ignore */ };
    return () => ws.close();
  }, []);

  return (
    <div className="p-4 bg-gray-900 shadow rounded-2xl">
      {/* --- Run Table --- */}
      <div className="flex items-end justify-between">
        <h2 className="text-xl font-bold mb-2 text-sky-400">EFP’s</h2>
        <div className="text-xs text-gray-400">
          {/* Columns: Bid | Offer | Cash Ref | Watchpoint */}
        </div>
      </div>
      <table className="w-full text-sm text-gray-200">
    <thead className="border-b border-gray-700">
      <tr>
        <th className="text-left p-2">EFP's</th>
        <th className="text-left p-2">Price</th>
        <th className="text-left p-2">Cash Ref</th>
        <th className="text-left p-2">Watchpoint</th>
        <th className="text-left p-2">Expiry</th>
      </tr>
    </thead>
    <tbody>
          {runRows.map((r, i) => (
    <tr key={i} className="border-b border-gray-700">
      <td className="p-2">{r.index_name +"  EFP"} </td>
      <td className="p-2">{(r.bid ?? "-")+" / " + (r.offer ?? "-")}</td>
      {/* <td className="p-2">{r.offer ?? "-"}</td> */}
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
              <td colSpan={5} className="p-3 text-center text-gray-500">
                No rows yet — try asking the AI to add one.
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
