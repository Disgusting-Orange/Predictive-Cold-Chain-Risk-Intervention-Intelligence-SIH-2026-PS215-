export interface Location {
  name: string;
  latitude: number;
  longitude: number;
  type?: string;
}

export interface ContributingFactor {
  direction: string;
  description: string;
}

export interface SHAPFactor {
  feature_name: string;
  display_name?: string;
  observed_value: number;
  shap_value: number;
  unit?: string;
  feature_group?: string;
}

export interface SHAPExplanation {
  top_risk_increasing_factors: SHAPFactor[];
  top_risk_reducing_factors: SHAPFactor[];
}

export interface ObservedEvent {
  event_type: string;
  severity: string;
  description: string;
  probe_name?: string;
  metric_value?: number;
}

export interface ProtectiveAction {
  state: string;
  requested_action: string;
  target_temperature_c?: number;
  cooling_power_level?: number;
  reasons: string[];
  issued_at?: string;
  disclaimer: string;
}

export interface EdgeStatus {
  network_mode: 'ONLINE' | 'LOCAL_ONLY' | 'EDGE_UNAVAILABLE' | 'DEGRADED';
  internet_connected: boolean;
  edge_gateway_reachable: boolean;
  sensor_connected: boolean;
  ml_available: boolean;
  cloud_sync_pending_count: number;
  active_shipments_count: number;
  uptime_seconds: number;
  status_updated_at: string;
}

export interface Shipment {
  shipmentId: string;
  vehicleId: string;
  productType: string;
  productName: string;
  origin: Location;
  destination: Location;
  latitude: number;
  longitude: number;
  temperature: number;
  humidity: number;
  speed: number;
  doorOpen: boolean;
  battery: number;
  etaMinutes: number;
  delayMinutes: number;
  status: string;
  riskScore: number;
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  temperatureTrend: number;
  estimatedCargoValue: number;
  safeMinTemp: number;
  safeMaxTemp: number;
  coolingPower: number;
  factors: ContributingFactor[];
  fusedState?: string;
  riskProbability?: number | null;
  threshold?: number;
  explanation?: SHAPExplanation | null;
  observedEvents?: ObservedEvent[];
  protectiveAction?: ProtectiveAction | null;
}

export interface Warehouse {
  warehouseId: string;
  name: string;
  location: Location;
  type: 'distribution' | 'cold_storage';
  temperature: number;
  humidity: number;
  capacity: number;
  activeBays: number;
  totalBays: number;
  coolingStatus: 'operational' | 'degraded' | 'offline';
  powerStatus: 'grid' | 'backup' | 'degraded';
  lastInspection: string;
  inventoryCount: number;
  tempSetpoint: number;
  safeMinTemp: number;
  safeMaxTemp: number;
}

export interface AIRecommendationAction {
  type: 'control' | 'intervene' | 'warehouse_control';
  targetId: string;
  params: Record<string, unknown>;
}

export interface AIRecommendation {
  id: string;
  type: string;
  targetType: 'shipment' | 'warehouse';
  targetId: string;
  targetName: string;
  priority: 'INFO' | 'WARNING' | 'URGENT';
  title: string;
  description: string;
  action: AIRecommendationAction | null;
  timestamp: string;
}

export interface ControlOverride {
  temperature?: number;
  humidity?: number;
  speed?: number;
  doorOpen?: boolean;
  battery?: number;
  coolingPower?: number;
}

export interface WarehouseControlOverride {
  temperature?: number;
  humidity?: number;
  capacity?: number;
  coolingStatus?: string;
  powerStatus?: string;
  tempSetpoint?: number;
  activeBays?: number;
}

export interface TemperatureReading {
  time: string;
  temperature: number;
  isPredicted: boolean;
}

export interface PredictedTemp {
  minutesAhead: number;
  temperature: number;
}

export interface Prediction {
  excursionRisk: number;
  timeToUnsafe: number | null;
  temperatureTrend: number;
  message: string;
  predictedTemperatures: PredictedTemp[];
}

export interface RouteOption {
  id: string;
  name: string;
  description: string;
  etaMinutes: number;
  predictedRisk: number;
  destination: Location;
  isRecommended: boolean;
}

export interface InterventionRecommendation {
  action: string;
  destination: string;
  reasons: string[];
  beforeRisk: number;
  afterRisk: number;
  beforeEta: number;
  afterEta: number;
}

export interface ImpactData {
  withoutIntervention: { risk: number; estimatedLoss: number };
  withIntervention: { risk: number; estimatedLoss: number };
  lossAvoided: number;
  riskReduction: number;
}

export interface Alert {
  id: string;
  shipmentId: string;
  message: string;
  severity: string;
  timestamp: string;
}

export interface KPIs {
  activeShipments: number;
  atRiskShipments: number;
  criticalShipments: number;
  estimatedLossAvoided: number;
  activeWarehouses: number;
  warehouseAlerts: number;
}

export interface SelectedDetail {
  temperatureHistory: TemperatureReading[];
  prediction: Prediction;
  routeOptions: RouteOption[] | null;
  intervention: InterventionRecommendation | null;
  impact: ImpactData | null;
  safeMinTemp: number;
  safeMaxTemp: number;
  fusedAssessment?: any;
  shapExplanation?: SHAPExplanation | null;
  protectiveAction?: ProtectiveAction | null;
}

export interface DashboardState {
  shipments: Shipment[];
  warehouses: Warehouse[];
  alerts: Alert[];
  aiRecommendations: AIRecommendation[];
  kpis: KPIs;
  scenario: string;
  interventionApplied: boolean;
  selectedShipmentId: string | null;
  selectedDetail: SelectedDetail | null;
  locations: Record<string, Location>;
  tick: number;
  edgeStatus?: EdgeStatus | null;
  networkMode?: 'ONLINE' | 'LOCAL_ONLY' | 'EDGE_UNAVAILABLE' | 'DEGRADED';
  cloudSyncPending?: number;
  mlAvailable?: boolean;
}

// Risk level color helpers
export const RISK_COLORS: Record<string, string> = {
  LOW: '#22c55e',
  MEDIUM: '#eab308',
  HIGH: '#f97316',
  CRITICAL: '#ef4444',
  INFO: '#3b82f6',
};

export const RISK_BG_COLORS: Record<string, string> = {
  LOW: 'rgba(34, 197, 94, 0.15)',
  MEDIUM: 'rgba(234, 179, 8, 0.15)',
  HIGH: 'rgba(249, 115, 22, 0.15)',
  CRITICAL: 'rgba(239, 68, 68, 0.15)',
  INFO: 'rgba(59, 130, 246, 0.15)',
};

export const PRIORITY_COLORS: Record<string, string> = {
  URGENT: '#ef4444',
  WARNING: '#f97316',
  INFO: '#3b82f6',
};

export const PRIORITY_BG_COLORS: Record<string, string> = {
  URGENT: 'rgba(239, 68, 68, 0.12)',
  WARNING: 'rgba(249, 115, 22, 0.12)',
  INFO: 'rgba(59, 130, 246, 0.12)',
};
