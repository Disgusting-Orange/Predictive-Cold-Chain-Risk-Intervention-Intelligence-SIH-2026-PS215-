import { useWebSocket } from './hooks/useWebSocket';
import KPICards from './components/KPICards';
import ShipmentMap from './components/ShipmentMap';
import ShipmentTable from './components/ShipmentTable';
import AlertPanel from './components/AlertPanel';
import ShipmentDetail from './components/ShipmentDetail';
import ScenarioControls from './components/ScenarioControls';
import WarehousePanel from './components/WarehousePanel';
import AIRecommendations from './components/AIRecommendations';
import { Snowflake, Wifi, WifiOff } from 'lucide-react';

export default function App() {
  const {
    state,
    connected,
    selectShipment,
    setScenario,
    applyIntervention,
    sendControl,
    sendWarehouseControl,
    toggleNetworkSimulation,
  } = useWebSocket();

  if (!state) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: '#0a0f1e' }}>
        <div className="text-center">
          <div className="animate-spin w-12 h-12 border-4 border-cyan-500 border-t-transparent rounded-full mx-auto mb-4" />
          <div className="text-slate-400 text-sm">
            Connecting to Cold-Chain Platform...
          </div>
          <div className="text-slate-600 text-xs mt-2">
            Ensure the backend is running on port 8000
          </div>
        </div>
      </div>
    );
  }

  const selectedShipment = state.shipments.find(
    (s) => s.shipmentId === state.selectedShipmentId
  );

  return (
    <div
      className="min-h-screen"
      style={{
        background: 'linear-gradient(135deg, #0a0f1e 0%, #0f172a 50%, #0a0f1e 100%)',
        color: '#e2e8f0',
      }}
    >
      {/* Header */}
      <header
        className="px-4 py-2.5 flex items-center justify-between border-b"
        style={{
          background: 'rgba(15,23,42,0.8)',
          borderColor: 'rgba(148,163,184,0.1)',
          backdropFilter: 'blur(12px)',
        }}
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-cyan-500/15">
            <Snowflake size={18} className="text-cyan-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-bold text-slate-100 tracking-wide">
                AI COLD CHAIN COMMAND CENTRE
              </h1>
              {/* Edge Network Mode Badge */}
              <span
                className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider"
                style={{
                  background:
                    state.networkMode === 'ONLINE'
                      ? 'rgba(34, 197, 94, 0.15)'
                      : state.networkMode === 'LOCAL_ONLY'
                        ? 'rgba(249, 115, 22, 0.15)'
                        : 'rgba(239, 68, 68, 0.15)',
                  color:
                    state.networkMode === 'ONLINE'
                      ? '#22c55e'
                      : state.networkMode === 'LOCAL_ONLY'
                        ? '#f97316'
                        : '#ef4444',
                  border: `1px solid ${
                    state.networkMode === 'ONLINE'
                      ? 'rgba(34, 197, 94, 0.3)'
                      : state.networkMode === 'LOCAL_ONLY'
                        ? 'rgba(249, 115, 22, 0.3)'
                        : 'rgba(239, 68, 68, 0.3)'
                  }`,
                }}
              >
                {state.networkMode === 'LOCAL_ONLY'
                  ? `⚡ Local Edge ML (Offline • ${state.cloudSyncPending || 0} Queued)`
                  : state.networkMode === 'ONLINE'
                    ? '🌐 Online (Cloud Synced)'
                    : state.networkMode || 'EDGE'}
              </span>
            </div>
            <p className="text-xs text-slate-500">
              FrostLink Phase 21 • Edge-Resilient Multi-Probe Architecture
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Internet Simulation Toggle */}
          <button
            onClick={() => toggleNetworkSimulation(state.networkMode === 'LOCAL_ONLY')}
            className="px-2.5 py-1 rounded text-xs font-semibold transition-all hover:scale-[1.02]"
            style={{
              background:
                state.networkMode === 'LOCAL_ONLY'
                  ? 'rgba(34, 197, 94, 0.15)'
                  : 'rgba(249, 115, 22, 0.15)',
              border: `1px solid ${
                state.networkMode === 'LOCAL_ONLY'
                  ? 'rgba(34, 197, 94, 0.3)'
                  : 'rgba(249, 115, 22, 0.3)'
              }`,
              color:
                state.networkMode === 'LOCAL_ONLY'
                  ? '#22c55e'
                  : '#f97316',
              cursor: 'pointer',
            }}
            title="Toggle Internet connectivity to demonstrate that Edge ML continues uninterrupted offline"
          >
            {state.networkMode === 'LOCAL_ONLY' ? '🔌 Restore Internet' : '📡 Drop Internet (Test Offline ML)'}
          </button>

          <ScenarioControls
            scenario={state.scenario}
            onScenario={setScenario}
          />
          <div className="flex items-center gap-1.5 ml-2">
            {connected ? (
              <>
                <Wifi size={12} className="text-green-400" />
                <span className="text-xs text-green-400">Live WS</span>
              </>
            ) : (
              <>
                <WifiOff size={12} className="text-red-400" />
                <span className="text-xs text-red-400">Disconnected</span>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="p-3">
        {/* KPI Cards */}
        <div className="mb-3">
          <KPICards
            kpis={state.kpis}
            aiRecommendationCount={state.aiRecommendations?.length || 0}
          />
        </div>

        {/* Three Column Layout */}
        <div className="flex gap-3" style={{ height: 'calc(100vh - 145px)' }}>
          {/* Left Column: AI Recommendations + Alerts */}
          <div className="flex flex-col gap-3 min-w-0" style={{ flex: '0 0 22%' }}>
            <AIRecommendations
              recommendations={state.aiRecommendations || []}
              onSendControl={sendControl}
              onSendWarehouseControl={sendWarehouseControl}
              onApplyIntervention={applyIntervention}
            />
            <AlertPanel alerts={state.alerts} />
          </div>

          {/* Middle Column: Map + Warehouses + Table */}
          <div className="flex-1 flex flex-col gap-3 min-w-0" style={{ flex: '0 0 42%' }}>
            <ShipmentMap
              shipments={state.shipments}
              warehouses={state.warehouses || []}
              locations={state.locations}
              selectedId={state.selectedShipmentId}
              onSelect={selectShipment}
            />
            <WarehousePanel warehouses={state.warehouses || []} />
            <ShipmentTable
              shipments={state.shipments}
              selectedId={state.selectedShipmentId}
              onSelect={selectShipment}
            />
          </div>

          {/* Right Column: Shipment Detail */}
          <div style={{ flex: '0 0 34%' }} className="min-w-0">
            {selectedShipment && state.selectedDetail ? (
              <ShipmentDetail
                shipment={selectedShipment}
                detail={state.selectedDetail}
                interventionApplied={state.interventionApplied}
                onApplyIntervention={() =>
                  applyIntervention(selectedShipment.shipmentId)
                }
                onSendControl={sendControl}
              />
            ) : (
              <div
                className="rounded-xl border flex items-center justify-center h-full"
                style={{
                  background: 'rgba(15,23,42,0.6)',
                  borderColor: 'rgba(148,163,184,0.12)',
                }}
              >
                <div className="text-center">
                  <Snowflake size={48} className="text-slate-700 mx-auto mb-3" />
                  <div className="text-slate-500 text-sm">
                    Select a shipment to view details
                  </div>
                  <div className="text-slate-600 text-xs mt-1">
                    Click on a vehicle on the map or a row in the table
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
