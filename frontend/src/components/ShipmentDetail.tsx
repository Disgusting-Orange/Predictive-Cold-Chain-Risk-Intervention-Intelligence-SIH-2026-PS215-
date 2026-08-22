import type { Shipment, SelectedDetail, ControlOverride } from '../types';
import { RISK_COLORS } from '../types';
import TelemetryCards from './TelemetryCards';
import TemperatureChart from './TemperatureChart';
import RiskPanel from './RiskPanel';
import PredictionPanel from './PredictionPanel';
import RouteOptions from './RouteOptions';
import InterventionPanel from './InterventionPanel';
import ImpactPanel from './ImpactPanel';
import ControlPanel from './ControlPanel';
import { MapPin, Truck, Package, ArrowRight } from 'lucide-react';

interface Props {
  shipment: Shipment;
  detail: SelectedDetail;
  interventionApplied: boolean;
  onApplyIntervention: () => void;
  onSendControl: (shipmentId: string, overrides: ControlOverride) => void;
}

export default function ShipmentDetail({
  shipment,
  detail,
  interventionApplied,
  onApplyIntervention,
  onSendControl,
}: Props) {
  const riskColor = RISK_COLORS[shipment.riskLevel] || '#94a3b8';

  return (
    <div className="space-y-3 overflow-auto pr-1" style={{ maxHeight: 'calc(100vh - 130px)' }}>
      {/* Header */}
      <div
        className="rounded-xl border p-4"
        style={{
          background: 'rgba(15,23,42,0.6)',
          borderColor: 'rgba(148,163,184,0.12)',
        }}
      >
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-lg flex items-center justify-center"
              style={{ background: `${riskColor}15` }}
            >
              <Truck size={20} style={{ color: riskColor }} />
            </div>
            <div>
              <div className="text-lg font-bold text-slate-100 font-mono">
                {shipment.shipmentId}
              </div>
              <div className="text-xs text-slate-500">
                Vehicle: {shipment.vehicleId}
              </div>
            </div>
          </div>
          <div
            className="px-3 py-1.5 rounded-lg text-sm font-bold uppercase"
            style={{
              color: riskColor,
              background: `${riskColor}15`,
              border: `1px solid ${riskColor}30`,
            }}
          >
            {shipment.status}
          </div>
        </div>

        <div className="flex items-center gap-3 text-sm">
          <div className="flex items-center gap-1.5">
            <Package size={12} className="text-blue-400" />
            <span className="text-slate-300">{shipment.productName}</span>
          </div>
          <span className="text-slate-600">|</span>
          <span className="text-slate-500 text-xs uppercase">
            {shipment.productType}
          </span>
        </div>

        <div className="flex items-center gap-2 mt-2 text-xs text-slate-400">
          <MapPin size={10} className="text-blue-400" />
          <span>{shipment.origin.name}</span>
          <ArrowRight size={10} />
          <MapPin size={10} className="text-purple-400" />
          <span>{shipment.destination.name}</span>
        </div>

        <div className="mt-2 text-xs text-slate-600">
          Cargo Value: ₹{shipment.estimatedCargoValue.toLocaleString('en-IN')}
          &nbsp;|&nbsp;
          Safe Range: {shipment.safeMinTemp}°C – {shipment.safeMaxTemp}°C
        </div>
      </div>

      {/* Telemetry Cards */}
      <TelemetryCards shipment={shipment} />

      {/* Vehicle Controls */}
      <ControlPanel shipment={shipment} onSendControl={onSendControl} />

      {/* Temperature Chart */}
      {detail.temperatureHistory.length > 0 && (
        <TemperatureChart
          history={detail.temperatureHistory}
          safeMin={detail.safeMinTemp}
          safeMax={detail.safeMaxTemp}
        />
      )}

      {/* Risk Panel */}
      <RiskPanel
        riskScore={shipment.riskScore}
        riskLevel={shipment.riskLevel}
        factors={shipment.factors}
      />

      {/* Prediction Panel */}
      {detail.prediction && (
        <PredictionPanel prediction={detail.prediction} />
      )}

      {/* Route Options */}
      {detail.routeOptions && (
        <RouteOptions options={detail.routeOptions} />
      )}

      {/* Intervention Panel */}
      {(detail.intervention || interventionApplied) && detail.intervention && (
        <InterventionPanel
          intervention={detail.intervention}
          interventionApplied={interventionApplied}
          onApply={onApplyIntervention}
        />
      )}

      {/* Impact Panel */}
      {detail.impact && (
        <ImpactPanel impact={detail.impact} />
      )}

      {/* Disclaimer */}
      <div className="text-xs text-slate-600 text-center py-2 italic">
        All values are prototype simulation estimates.
        Not validated real-world data. Temperature ranges shown
        do not constitute medical guidance.
      </div>
    </div>
  );
}
