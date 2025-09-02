
import { useEffect, useState } from "react";

type Recap = { index_name: string; price: number; lots: number; cash_ref: number | null; recap_text: string; };

export default function RecapLog() {
  const [rows, setRows] = useState<Recap[]>([]);

  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/api/efp/ws/recaps`);
    ws.onmessage = (e) => setRows(JSON.parse(e.data));
    ws.onerror = () => {/* ignore */};
    return () => ws.close();
  }, []);

  return (
   <div className="p-4 bg-gray-900 shadow rounded-2xl">
  <h2 className="text-xl font-bold mb-2 text-sky-400">Trade Recap</h2>
  <ul className="space-y-2 text-gray-200">

        {rows.map((r, i) => (
          <li key={i} className="text-sm">
            <span className="font-semibold">{r.index_name}</span>: {r.recap_text}
          </li>
        ))}
        {rows.length === 0 && <li className="text-sm text-slate-500">No trades yet.</li>}
      </ul>
    </div>
  );
}
