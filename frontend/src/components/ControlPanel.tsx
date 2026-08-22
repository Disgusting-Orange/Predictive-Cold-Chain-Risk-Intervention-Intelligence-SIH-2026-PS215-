import { useState, useCallback } from 'react';
import type { Shipment, ControlOverride } from '../types';
import { RISK_COLORS } from '../types';
import {
  Thermometer,
  Droplets,
  Gauge,
  DoorOpen,
  DoorClosed,
  Snowflake,
  Send,
  RotateCcw,
} from 'lucide-react';

interface Props {
  shipment: Shipment;
  onSendControl: (shipmentId: string, overrides: ControlOverride) => void;
}

export default function ControlPanel({ shipment, onSendControl }: Props) {
  const [temperature, setTemperature] = useState(shipment.temperature);
  const [humidity, setHumidity] = useState(shipment.humidity);
  const [speed, setSpeed] = useState(shipment.speed);
  const [coolingPower, setCoolingPower] = useState(shipment.coolingPower);
  const [doorOpen, setDoorOpen] = useState(shipment.doorOpen);
  const [dirty, setDirty] = useState(false);

  const markDirty = useCallback(() => setDirty(true), []);

  const handleApply = useCallback(() => {
    const overrides: ControlOverride = {};
    if (temperature !== shipment.temperature) overrides.temperature = temperature;
    if (humidity !== shipment.humidity) overrides.humidity = humidity;
    if (speed !== shipment.speed) overrides.speed = speed;
    if (coolingPower !== shipment.coolingPower) overrides.coolingPower = coolingPower;
    if (doorOpen !== shipment.doorOpen) overrides.doorOpen = doorOpen;

    if (Object.keys(overrides).length > 0) {
      onSendControl(shipment.shipmentId, overrides);
      setDirty(false);
    }
  }, [temperature, humidity, speed, coolingPower, doorOpen, shipment, onSendControl]);

  const handleReset = useCallback(() => {
    setTemperature(shipment.temperature);
    setHumidity(shipment.humidity);
    setSpeed(shipment.speed);
    setCoolingPower(shipment.coolingPower);
    setDoorOpen(shipment.doorOpen);
    setDirty(false);
  }, [shipment]);

  // Cooling power color
  const coolingColor =
    coolingPower >= 80
      ? '#22c55e'
      : coolingPower >= 50
        ? '#eab308'
        : RISK_COLORS.CRITICAL;

  return (
    <div
      className="rounded-xl border p-4"
      style={{
        background: 'rgba(15,23,42,0.6)',
        borderColor: 'rgba(148,163,184,0.12)',
      }}
    >
      <div className="flex items-center gap-2 mb-3">
        <Snowflake size={14} className="text-cyan-400" />
        <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
          Vehicle Controls
        </span>
        <span className="ml-auto text-xs text-slate-600">
          Manual override
        </span>
      </div>

      <div className="space-y-3">
        {/* Temperature Slider */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-1.5 text-xs text-slate-400">
              <Thermometer size={12} />
              Temperature
            </div>
            <span className="text-sm font-mono font-bold text-slate-200">
              {temperature.toFixed(1)}°C
            </span>
          </div>
          <input
            type="range"
            min={shipment.safeMinTemp - 3}
            max={shipment.safeMaxTemp + 5}
            step={0.1}
            value={temperature}
            onChange={(e) => {
              setTemperature(parseFloat(e.target.value));
              markDirty();
            }}
            className="control-slider"
            style={{
              width: '100%',
              accentColor:
                temperature >= shipment.safeMaxTemp
                  ? RISK_COLORS.CRITICAL
                  : temperature >= shipment.safeMaxTemp - 1
                    ? RISK_COLORS.HIGH
                    : '#06b6d4',
            }}
          />
          <div className="flex justify-between text-xs text-slate-600 mt-0.5">
            <span>{(shipment.safeMinTemp - 3).toFixed(0)}°C</span>
            <span
              className="px-1 rounded"
              style={{
                background: 'rgba(34,197,94,0.1)',
                color: '#22c55e',
              }}
            >
              Safe: {shipment.safeMinTemp}–{shipment.safeMaxTemp}°C
            </span>
            <span>{(shipment.safeMaxTemp + 5).toFixed(0)}°C</span>
          </div>
        </div>

        {/* Cooling Power Slider */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-1.5 text-xs text-slate-400">
              <Snowflake size={12} />
              Cooling Power
            </div>
            <span
              className="text-sm font-mono font-bold"
              style={{ color: coolingColor }}
            >
              {coolingPower}%
            </span>
          </div>
          <input
            type="range"
            min={0}
            max={100}
            step={5}
            value={coolingPower}
            onChange={(e) => {
              setCoolingPower(parseInt(e.target.value));
              markDirty();
            }}
            className="control-slider"
            style={{ width: '100%', accentColor: coolingColor }}
          />
          <div className="flex justify-between text-xs text-slate-600 mt-0.5">
            <span>0% (Off)</span>
            <span>100% (Max)</span>
          </div>
        </div>

        {/* Two column: Humidity + Speed */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-1.5 text-xs text-slate-400">
                <Droplets size={12} />
                Humidity
              </div>
              <span className="text-sm font-mono font-bold text-slate-200">
                {humidity}%
              </span>
            </div>
            <input
              type="range"
              min={10}
              max={90}
              step={1}
              value={humidity}
              onChange={(e) => {
                setHumidity(parseInt(e.target.value));
                markDirty();
              }}
              className="control-slider"
              style={{ width: '100%', accentColor: '#3b82f6' }}
            />
          </div>
          <div>
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-1.5 text-xs text-slate-400">
                <Gauge size={12} />
                Speed
              </div>
              <span className="text-sm font-mono font-bold text-slate-200">
                {speed} km/h
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={80}
              step={1}
              value={speed}
              onChange={(e) => {
                setSpeed(parseInt(e.target.value));
                markDirty();
              }}
              className="control-slider"
              style={{
                width: '100%',
                accentColor: speed < 10 ? RISK_COLORS.MEDIUM : '#8b5cf6',
              }}
            />
          </div>
        </div>

        {/* Door Toggle */}
        <div
          className="rounded-lg px-3 py-2.5 flex items-center justify-between border"
          style={{
            background: doorOpen
              ? 'rgba(239,68,68,0.06)'
              : 'rgba(34,197,94,0.06)',
            borderColor: doorOpen
              ? 'rgba(239,68,68,0.15)'
              : 'rgba(34,197,94,0.15)',
          }}
        >
          <div className="flex items-center gap-2">
            {doorOpen ? (
              <DoorOpen size={16} className="text-red-400" />
            ) : (
              <DoorClosed size={16} className="text-green-400" />
            )}
            <span className="text-sm text-slate-200">Cargo Door</span>
          </div>
          <button
            onClick={() => {
              setDoorOpen(!doorOpen);
              markDirty();
            }}
            className="relative w-11 h-6 rounded-full transition-colors"
            style={{
              background: doorOpen
                ? 'rgba(239,68,68,0.4)'
                : 'rgba(34,197,94,0.4)',
              border: `1px solid ${
                doorOpen ? 'rgba(239,68,68,0.5)' : 'rgba(34,197,94,0.5)'
              }`,
              cursor: 'pointer',
            }}
          >
            <div
              className="absolute top-0.5 w-4.5 h-4.5 rounded-full transition-all"
              style={{
                width: '18px',
                height: '18px',
                background: doorOpen ? '#ef4444' : '#22c55e',
                left: doorOpen ? '22px' : '2px',
                boxShadow: '0 1px 3px rgba(0,0,0,0.3)',
              }}
            />
          </button>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2">
          <button
            onClick={handleApply}
            disabled={!dirty}
            className="flex-1 py-2 rounded-lg text-sm font-bold uppercase tracking-wider flex items-center justify-center gap-2 transition-all"
            style={{
              background: dirty
                ? 'linear-gradient(135deg, #06b6d4, #3b82f6)'
                : 'rgba(30,41,59,0.5)',
              color: dirty ? 'white' : '#475569',
              border: dirty
                ? '1px solid rgba(6,182,212,0.3)'
                : '1px solid rgba(148,163,184,0.1)',
              cursor: dirty ? 'pointer' : 'default',
              boxShadow: dirty ? '0 4px 15px rgba(6,182,212,0.2)' : 'none',
              opacity: dirty ? 1 : 0.5,
            }}
          >
            <Send size={14} />
            Apply Controls
          </button>
          <button
            onClick={handleReset}
            className="px-3 py-2 rounded-lg text-sm transition-all hover:scale-[1.03]"
            style={{
              background: 'rgba(30,41,59,0.5)',
              color: '#94a3b8',
              border: '1px solid rgba(148,163,184,0.1)',
              cursor: 'pointer',
            }}
          >
            <RotateCcw size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
