import { useEffect, useState } from "react";

type BlotterTrade = {
  id: number;
  side: string;
  index_name: string;
  qty: number;
  avg_price: number;
  created_at: string;
};

export default function BlotterPanel() {
  const [trades, setTrades] = useState<BlotterTrade[]>([]);

  useEffect(() => {
    const ws = new WebSocket("wss://efp-machine-2.onrender.com/api/blotter/ws/list");

    ws.onmessage = (e) => {
      const data: BlotterTrade[] = JSON.parse(e.data);
      setTrades(data);
    };

    ws.onerror = () => console.warn("Blotter WS error");
    ws.onclose = () => console.log("Blotter WS closed");

    return () => ws.close();
  }, []);

  return (
    <div className="p-4 bg-gray-900 rounded-2xl text-gray-200">
      <h2 className="text-xl font-bold text-sky-400 mb-3">Blotter</h2>
      {trades.length === 0 ? (
        <div>No trades yet.</div>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-700">
              <th className="p-2">Side</th>
              <th className="p-2">Index</th>
              <th className="p-2">Qty</th>
              <th className="p-2">Avg Price</th>
              <th className="p-2">Time</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((t) => (
              <tr key={t.id} className="border-b border-gray-800">
                <td className="p-2">{t.side}</td>
                <td className="p-2">{t.index_name}</td>
                <td className="p-2">{t.qty}</td>
                <td className="p-2">{t.avg_price}</td>
                <td className="p-2">
                  {new Date(t.created_at).toLocaleTimeString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
