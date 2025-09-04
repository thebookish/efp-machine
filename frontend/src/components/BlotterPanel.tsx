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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

  const fetchTrades = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/api/blotter/list`);
      if (!res.ok) throw new Error("Failed to load trades");
      const data = await res.json();
      setTrades(data);
    } catch (err: any) {
      setError(err.message || "Error loading trades");
    } finally {
      setLoading(false);
    }
  };

  const removeTrade = async (id: number) => {
    try {
      await fetch(`${API_BASE}/api/blotter/remove`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trade_id: id }),
      });
      fetchTrades();
    } catch (err) {
      console.error("Failed to remove trade:", err);
    }
  };

  useEffect(() => {
    fetchTrades();
    // const interval = setInterval(fetchTrades, 5000); // auto-refresh
    // return () => clearInterval(interval);
  }, []);

  return (
    <div className="p-4 bg-gray-900 shadow rounded-2xl">
      <h2 className="text-xl font-bold mb-4 text-sky-400">Trade Blotter</h2>

      {loading && <div className="text-gray-400 text-sm">Loading...</div>}
      {error && <div className="text-red-500 text-sm">{error}</div>}

      <table className="w-full text-sm text-gray-200">
        <thead className="border-b border-gray-700">
          <tr>
            <th className="p-2 text-left">#</th>
            <th className="p-2 text-left">Side</th>
            <th className="p-2 text-left">Index</th>
            <th className="p-2 text-left">Qty</th>
            <th className="p-2 text-left">Avg Price</th>
            <th className="p-2 text-left">Time</th>
            <th className="p-2 text-left">Action</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((t) => (
            <tr key={t.id} className="border-b border-gray-800">
              <td className="p-2">{t.id}</td>
              <td
                className={`p-2 font-semibold ${
                  t.side === "BUY" ? "text-green-400" : "text-red-400"
                }`}
              >
                {t.side}
              </td>
              <td className="p-2">{t.index_name}</td>
              <td className="p-2">{t.qty}</td>
              <td className="p-2">{t.avg_price.toFixed(2)}</td>
              <td className="p-2">
                {new Date(t.created_at).toLocaleTimeString()}
              </td>
              <td className="p-2">
                <button
                  onClick={() => removeTrade(t.id)}
                  className="px-2 py-1 text-xs bg-red-600 hover:bg-red-700 rounded-lg"
                >
                  Remove
                </button>
              </td>
            </tr>
          ))}
          {trades.length === 0 && !loading && (
            <tr>
              <td colSpan={7} className="p-3 text-center text-gray-500">
                No trades yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
