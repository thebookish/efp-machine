import { useEffect, useState } from "react";

export default function RatesPanel() {
  const [rates, setRates] = useState<{SONIA:number|null, EURIBOR_3M:number|null}>({
    SONIA: null,
    EURIBOR_3M: null,
  });

  useEffect(() => {
    const load = () => {
      fetch("http://localhost:8000/api/efp/rates")
        .then((r) => r.json())
        .then(setRates)
        .catch(() => {});
    };
    load();
    const id = setInterval(load, 60_000); // refresh every minute
    return () => clearInterval(id);
  }, []);

  return (
    <div className="p-4 bg-gray-900 shadow rounded-2xl">
      <h2 className="text-xl font-bold mb-2 text-sky-400">Rates Monitor</h2>
      <div className="space-y-1 text-gray-200">
        <div>SONIA: {rates.SONIA ?? "-"}</div>
        <div>Euribor 3M: {rates.EURIBOR_3M ?? "-"}</div>
      </div>
    </div>
  );
}
