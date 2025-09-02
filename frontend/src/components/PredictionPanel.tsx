import { useEffect, useState } from "react";

type Prediction = {
  index_name: string;
  bid: number | null;
  offer: number | null;
  cash_ref: number | null;
  theo_bid: number | null;
  theo_offer: number | null;
  watchpoint: boolean;
  expiry: { index: string; status: string; expiry_date: string | null };
};

type TRFRun = {
  index: string;
  basis: number;
};

type Payload = {
  predicted_run: Prediction[];
  trf_run: TRFRun;
  recaps: { index_name: string; recap_text: string; created_at: string }[];
  timestamp: string;
};

export default function PredictionPanel() {
  const [data, setData] = useState<Payload | null>(null);

  useEffect(() => {
    // For now poll a REST endpoint instead of WS
    const interval = setInterval(async () => {
      try {
        const res = await fetch("http://localhost:8000/api/efp/prediction");
        if (res.ok) {
          const json = await res.json();
          setData(json);
        }
      } catch {}
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  if (!data) return <div className="p-4 bg-gray-900 rounded-xl text-gray-400">No prediction yet.</div>;

  return (
    <div className="p-4 bg-gray-900 shadow rounded-2xl">
      <h2 className="text-xl font-bold text-sky-400 mb-2">07:50 Prediction Run</h2>
      <div className="text-xs text-gray-400 mb-2">Published: {new Date(data.timestamp).toLocaleTimeString()}</div>
      
      <table className="w-full text-sm text-gray-200 mb-4">
        <thead>
          <tr>
            <th className="p-2">Index</th>
            <th className="p-2">Bid</th>
            <th className="p-2">Offer</th>
            <th className="p-2">Theo Bid</th>
            <th className="p-2">Theo Offer</th>
            <th className="p-2">Watch</th>
            <th className="p-2">Expiry</th>
          </tr>
        </thead>
        <tbody>
          {data.predicted_run.map((p, i) => (
            <tr key={i} className="border-b border-gray-700">
              <td className="p-2">{p.index_name}</td>
              <td className="p-2">{p.bid ?? "-"}</td>
              <td className="p-2">{p.offer ?? "-"}</td>
              <td className="p-2">{p.theo_bid ?? "-"}</td>
              <td className="p-2">{p.theo_offer ?? "-"}</td>
              <td className="p-2">{p.watchpoint ? "⚠" : "-"}</td>
              <td className="p-2">{p.expiry.status}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="mb-2">
        <h3 className="text-lg text-sky-400">SX5E TRF Run</h3>
        <p className="text-gray-200">Basis: {data.trf_run.basis}</p>
      </div>

      <div>
        <h3 className="text-lg text-sky-400 mb-1">Prior-day Recaps</h3>
        <ul className="text-sm text-gray-200 space-y-1">
          {data.recaps.map((r, i) => (
            <li key={i}>
              {r.index_name} → {r.recap_text}{" "}
              <span className="text-xs text-gray-500">({new Date(r.created_at).toLocaleString()})</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
