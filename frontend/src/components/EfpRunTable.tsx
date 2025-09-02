
import { useEffect, useState } from "react";

type Row = { index_name: string; bid: number | null; offer: number | null; cash_ref: number | null; };

export default function EfpRunTable() {
  const [rows, setRows] = useState<Row[]>([]);

  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/api/efp/ws/run`);
    ws.onmessage = (e) => setRows(JSON.parse(e.data));
    ws.onerror = () => {/* ignore */};
    return () => ws.close();
  }, []);

  return (
    <div className="p-4 bg-white shadow rounded-2xl">
      <div className="flex items-end justify-between">
        <h2 className="text-xl font-bold mb-2">EFP’s</h2>
        <div className="text-xs text-slate-500">Columns: EFP’s | Price | Cash Ref</div>
      </div>
      <table className="w-full text-sm">
        <thead className="border-b">
          <tr>
            <th className="text-left p-2">Index</th>
            <th className="text-left p-2">Bid</th>
            <th className="text-left p-2">Offer</th>
            <th className="text-left p-2">Cash Ref</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-b">
              <td className="p-2">{r.index_name}</td>
              <td className="p-2">{r.bid ?? '-'}</td>
              <td className="p-2">{r.offer ?? '-'}</td>
              <td className="p-2">{r.cash_ref ?? '-'}</td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr>
              <td colSpan={4} className="p-3 text-center text-slate-500">No rows yet — try asking the AI to add one.</td>
            </tr>
          )}
        </tbody>
      </table>
      <div className="text-xs text-slate-500 mt-2">* SX7E section always appears last.</div>
    </div>
  );
}
