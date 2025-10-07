import AtomicClock from "./components/AtomicClock";
import EfpRunTable from "./components/EfpRunTable";
import RecapLog from "./components/RecapLog";
import ChatPanel from "./components/ChatPanel";
// import RatesPanel from "./components/RatesPanel";
import MarketValuesPanel from "./components/MarketValuesPanel";
import PredictionPanel from "./components/PredictionPanel";
import BlotterPanel from "./components/BlotterPanel";
import UploadJson from "./components/bbg_upload";
import Orders from "./components/Orders";
import BloombergMessagesPanel from "./components/BloombergMessage";

export default function App() {
  return (
<div className="min-h-screen bg-black text-gray-100">
      <div className="max-w-7xl mx-auto p-6 space-y-6">
        <div className="flex gap-4">
          <AtomicClock />
          {/* <RatesPanel /> */}
          {/* <MarketValuesPanel /> */}
         
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
<div className="md:col-span-3 h-[400px] flex flex-col">
  <ChatPanel />
</div>
          <div className="md:col-span-2 space-y-6">
            {/* <EfpRunTable /> */}
            {/* <RecapLog /> */}
          </div>
        </div>
        <div className="md:col-span-2 space-y-6">
          {/* <UploadJson/> */}
           {/* <PredictionPanel/> */}
           {/* <Orders/> */}
          {/* <BlotterPanel /> */}
          {/* <BloombergMessagesPanel></BloombergMessagesPanel> */}
        </div>
      </div>
    </div>
  );
}
