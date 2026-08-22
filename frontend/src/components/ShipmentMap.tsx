import { useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import type { Shipment, Location, Warehouse } from '../types';
import { RISK_COLORS } from '../types';
import 'leaflet/dist/leaflet.css';

interface Props {
  shipments: Shipment[];
  warehouses: Warehouse[];
  locations: Record<string, Location>;
  selectedId: string | null;
  onSelect: (id: string) => void;
}

// Custom vehicle icon using SVG data URI
function createVehicleIcon(riskLevel: string, isSelected: boolean) {
  const color = RISK_COLORS[riskLevel] || '#3b82f6';
  const size = isSelected ? 32 : 24;
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 24 24" fill="${color}" stroke="${isSelected ? '#fff' : '#0f172a'}" stroke-width="${isSelected ? 2 : 1.5}">
      <rect x="1" y="3" width="15" height="13" rx="2" ry="2"/>
      <polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/>
      <circle cx="5.5" cy="18.5" r="2.5" fill="${color}" stroke="${isSelected ? '#fff' : '#0f172a'}"/>
      <circle cx="18.5" cy="18.5" r="2.5" fill="${color}" stroke="${isSelected ? '#fff' : '#0f172a'}"/>
    </svg>
  `;
  return L.divIcon({
    html: `<div style="
      display:flex;align-items:center;justify-content:center;
      filter: drop-shadow(0 2px 4px rgba(0,0,0,0.5));
      ${isSelected ? 'animation: pulse 1.5s ease-in-out infinite;' : ''}
    ">${svg}</div>`,
    className: '',
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

// Facility icons
function createFacilityIcon(type: string) {
  const colors: Record<string, string> = {
    origin: '#3b82f6',
    destination: '#8b5cf6',
    cold_storage: '#06b6d4',
  };
  const color = colors[type] || '#64748b';

  return L.divIcon({
    html: `<div style="
      width:12px;height:12px;border-radius:3px;
      background:${color};border:2px solid #fff;
      box-shadow: 0 2px 4px rgba(0,0,0,0.4);
    "></div>`,
    className: '',
    iconSize: [12, 12],
    iconAnchor: [6, 6],
  });
}

// Warehouse icon — building shape
function createWarehouseIcon(coolingStatus: string) {
  const statusColor: Record<string, string> = {
    operational: '#22c55e',
    degraded: '#f97316',
    offline: '#ef4444',
  };
  const color = statusColor[coolingStatus] || '#8b5cf6';

  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
      <rect x="2" y="7" width="20" height="14" rx="2" fill="${color}22"/>
      <path d="M12 2 L2 7 L22 7 Z" fill="${color}33" stroke="${color}"/>
      <line x1="6" y1="11" x2="6" y2="17" stroke="${color}" stroke-width="1.5"/>
      <line x1="10" y1="11" x2="10" y2="17" stroke="${color}" stroke-width="1.5"/>
      <line x1="14" y1="11" x2="14" y2="17" stroke="${color}" stroke-width="1.5"/>
      <line x1="18" y1="11" x2="18" y2="17" stroke="${color}" stroke-width="1.5"/>
      <circle cx="20" cy="5" r="3" fill="${color}" stroke="white" stroke-width="1.5"/>
    </svg>
  `;

  return L.divIcon({
    html: `<div style="
      display:flex;align-items:center;justify-content:center;
      filter: drop-shadow(0 2px 6px rgba(0,0,0,0.5));
    ">${svg}</div>`,
    className: '',
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
}

// Component to fit map bounds
function MapBounds({ shipments, locations }: { shipments: Shipment[]; locations: Record<string, Location> }) {
  const map = useMap();

  useEffect(() => {
    const points: [number, number][] = [];
    shipments.forEach((s) => {
      points.push([s.latitude, s.longitude]);
    });
    Object.values(locations).forEach((loc) => {
      points.push([loc.latitude, loc.longitude]);
    });

    if (points.length > 0) {
      const bounds = L.latLngBounds(points);
      map.fitBounds(bounds, { padding: [30, 30] });
    }
  }, []); // Only on mount

  return null;
}

export default function ShipmentMap({ shipments, warehouses, locations, selectedId, onSelect }: Props) {
  const center: [number, number] = [13.06, 80.24];

  return (
    <div
      className="rounded-xl border overflow-hidden"
      style={{
        background: 'rgba(15,23,42,0.6)',
        borderColor: 'rgba(148,163,184,0.12)',
        height: '320px',
      }}
    >
      <style>
        {`
          @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.15); }
          }
          .leaflet-container {
            background: #0f172a !important;
          }
        `}
      </style>
      <MapContainer
        center={center}
        zoom={12}
        style={{ height: '100%', width: '100%' }}
        zoomControl={false}
        attributionControl={false}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />
        <MapBounds shipments={shipments} locations={locations} />

        {/* Facility markers */}
        {Object.entries(locations).map(([key, loc]) => (
          <Marker
            key={key}
            position={[loc.latitude, loc.longitude]}
            icon={createFacilityIcon(loc.type || 'origin')}
          >
            <Popup>
              <div style={{ fontSize: '12px', fontWeight: 600 }}>
                {loc.name}
              </div>
              <div style={{ fontSize: '10px', color: '#666', textTransform: 'uppercase' }}>
                {loc.type?.replace('_', ' ')}
              </div>
            </Popup>
          </Marker>
        ))}

        {/* Warehouse markers */}
        {warehouses.map((wh) => (
          <Marker
            key={wh.warehouseId}
            position={[wh.location.latitude, wh.location.longitude]}
            icon={createWarehouseIcon(wh.coolingStatus)}
          >
            <Popup>
              <div style={{ fontSize: '12px' }}>
                <div style={{ fontWeight: 700, marginBottom: '4px' }}>{wh.name}</div>
                <div style={{ display: 'flex', gap: '8px', marginBottom: '2px' }}>
                  <span>🌡️ {wh.temperature.toFixed(1)}°C</span>
                  <span>💧 {wh.humidity}%</span>
                </div>
                <div style={{ display: 'flex', gap: '8px', marginBottom: '2px' }}>
                  <span>📦 {wh.capacity}% capacity</span>
                  <span>🏗️ {wh.activeBays}/{wh.totalBays} bays</span>
                </div>
                <div style={{
                  marginTop: '4px',
                  padding: '2px 6px',
                  borderRadius: '4px',
                  fontSize: '10px',
                  fontWeight: 600,
                  display: 'inline-block',
                  background: wh.coolingStatus === 'operational' ? '#dcfce7' : '#fef3c7',
                  color: wh.coolingStatus === 'operational' ? '#166534' : '#92400e',
                }}>
                  Cooling: {wh.coolingStatus.toUpperCase()}
                </div>
              </div>
            </Popup>
          </Marker>
        ))}

        {/* Vehicle markers */}
        {shipments.map((s) => (
          <Marker
            key={s.shipmentId}
            position={[s.latitude, s.longitude]}
            icon={createVehicleIcon(s.riskLevel, selectedId === s.shipmentId)}
            eventHandlers={{
              click: () => onSelect(s.shipmentId),
            }}
          >
            <Popup>
              <div style={{ fontSize: '12px' }}>
                <div style={{ fontWeight: 700 }}>{s.shipmentId}</div>
                <div>{s.productName}</div>
                <div>Temp: {s.temperature.toFixed(1)}°C</div>
                <div>Risk: {s.riskLevel} ({s.riskScore}%)</div>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
