
import { useState } from "react";
import { askAI } from "../lib/api";

export default function ChatPanel() {
  const [input, setInput] = useState('');
  const [log, setLog] = useState<{role:'user'|'ai', text:string}[]>([]);

  const send = async () => {
    if (!input.trim()) return;
    const user = input;
    setInput('');
    setLog(l => [...l, {role:'user', text:user}]);
    try {
      const resp = await askAI(user);
      const text = resp.detail || resp.reply || JSON.stringify(resp);
      setLog(l => [...l, {role:'ai', text}]);
    } catch (e:any) {
      setLog(l => [...l, {role:'ai', text:'Error: ' + (e?.message || 'unknown') }]);
    }
  };

  const onKey = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') send();
  };

  return (
    <div className="p-4 bg-white shadow rounded-2xl h-full flex flex-col">
      <h2 className="text-xl font-bold mb-2">AI Assistant</h2>
      <div className="flex-1 overflow-auto space-y-2 mb-3">
        {log.map((m,i) => (
          <div key={i} className={m.role === 'user' ? 'text-right' : 'text-left'}>
            <span className={"inline-block px-3 py-2 rounded-2xl " + (m.role === 'user' ? 'bg-sky-100' : 'bg-slate-100') }>
              {m.text}
            </span>
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <input className="flex-1 border rounded-xl px-3 py-2" value={input} onChange={e=>setInput(e.target.value)} onKeyDown={onKey} placeholder="e.g., Update SX5E bid to -3.25 (cash ref 4210.5)" />
        <button className="px-4 py-2 rounded-xl bg-black text-white" onClick={send}>Send</button>
      </div>
    </div>
  );
}
