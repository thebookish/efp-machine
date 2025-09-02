
import AtomicClock from "./components/AtomicClock";
import EfpRunTable from "./components/EfpRunTable";
import RecapLog from "./components/RecapLog";
import ChatPanel from "./components/ChatPanel";

export default function App() {
  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      <div className="flex gap-4">
        <AtomicClock />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
         <div className="md:col-span-1">
          <ChatPanel />
        </div>
        <div className="md:col-span-2 space-y-6">
          <EfpRunTable />
          <RecapLog />
        </div>
       
      </div>
    </div>
  );
}
