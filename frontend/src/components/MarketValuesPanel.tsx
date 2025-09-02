import { useEffect, useState } from "react";

type Values = {
  SX5E: number | null;
  SX7E: number | null;
  DAX: number | null;
  FTSE: number | null;
  CAC: number | null;
};

export default function MarketValuesPanel() {
  const [values, setValues] = useState<Values>({
    SX5E: null,
    SX7E: null,
    DAX: null,
    FTSE: null,
    CAC: null,
  });

  useEffect(() => {
    const load = () => {
      fetch("http://localhost:8000/api/efp/market-values")
        .then((r) => r.json())
        .then(setValues)
        .catch(() => {});
    };
    load();
    const id = setInterval(load, 60_000); // refresh every minute
    return () => clearInterval(id);
  }, []);

  return (
    <div className="p-4 bg-gray-900 shadow rounded-2xl">
      <h2 className="text-xl font-bold mb-2 text-sky-400">Market Values</h2>
      <ul className="space-y-1 text-gray-200">
        <li>SX5E: {values.SX5E ?? "-"}</li>
        <li>SX7E: {values.SX7E ?? "-"}</li>
        <li>DAX: {values.DAX ?? "-"}</li>
        <li>FTSE: {values.FTSE ?? "-"}</li>
        <li>CAC: {values.CAC ?? "-"}</li>
      </ul>
    </div>
  );
}
