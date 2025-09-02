
import { useEffect, useState } from "react";

export default function AtomicClock() {
  const [now, setNow] = useState<string>('');
  useEffect(() => {
    const tick = () => {
      const uk = new Intl.DateTimeFormat('en-GB', {
        timeZone: 'Europe/London',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
      }).format(new Date());
      setNow(uk);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

 return (
  <div className="p-3 bg-gray-900 rounded-2xl shadow text-sm">
    <span className="font-semibold text-sky-400">UK Atomic Clock:</span> {now} BST
  </div>
);

}
