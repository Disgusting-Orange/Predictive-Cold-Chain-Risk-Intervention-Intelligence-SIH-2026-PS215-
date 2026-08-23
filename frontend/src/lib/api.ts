/**
 * Central API Client for Cold Chain AI platform.
 * Transparently wraps HTTP fetch requests with Bearer tokens and handles WebSocket telemetry streams.
 */

const API_BASE_URL = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

const apiUrl = (path: string) => `${API_BASE_URL}${path}`;

const getAuthHeaders = (): HeadersInit => {
  const token = localStorage.getItem("token");
  return token ? { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" } : { "Content-Type": "application/json" };
};

export interface UserResponse {
  id: string;
  email: string;
  full_name: string;
  role: "ADMIN" | "FIELD_AGENT" | "CLIENT";
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  email: string;
  full_name: string;
  role: "ADMIN" | "FIELD_AGENT" | "CLIENT";
}

export interface ProductProfile {
  id: string;
  name: string;
  category: string;
  safeTempMin: number;
  safeTempMax: number;
  criticalTempMax: number;
  safeHumidityMin: number;
  safeHumidityMax: number;
  temperatureSensitivity: string;
  shelfLifeHours: number;
}

export interface Location {
  name: string;
  latitude: number;
  longitude: number;
  type: string;
}

export interface Shipment {
  id: string;
  shipmentId: string;
  productName: string;
  productType: string;
  vehicleId: string;
  origin: Location;
  destination: Location;
  latitude: number;
  longitude: number;
  temperature: number;
  humidity: number;
  speed: number;
  doorOpen: boolean;
  coolingPower: number;
  battery: number;
  status: "IN_TRANSIT" | "DIVERTED" | "DELIVERED" | "CRITICAL";
  riskScore: number;
  riskLevel: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  plannedEtaMinutes: number;
  etaMinutes: number;
  delayMinutes: number;
  estimatedCargoValue: number;
  safeMinTemp: number;
  safeMaxTemp: number;
  remainingSafeLifeMinutes: number | null;
}

export interface SimulationScenario {
  scenarioName: string;
  projectedRiskScore: number;
  projectedEtaMinutes: number;
  projectedLossAvoided: number;
  description: string;
  isRecommended: boolean;
}

export interface WhatIfSimulationResponse {
  shipmentCode: string;
  scenarios: SimulationScenario[];
}

export const api = {
  // Authentication
  async login(email: string, password: string): Promise<TokenResponse> {
    const res = await fetch(apiUrl("/api/auth/login"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Authentication failed");
    }
    const data: TokenResponse = await res.json();
    localStorage.setItem("token", data.access_token);
    localStorage.setItem("user_role", data.role);
    localStorage.setItem("user_name", data.full_name);
    return data;
  },

  async register(payload: { email: string; password_hash?: string; password?: string; full_name: string; role: string; phone?: string }): Promise<TokenResponse> {
    const res = await fetch(apiUrl("/api/auth/register"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: payload.email,
        password: payload.password || payload.password_hash,
        full_name: payload.full_name,
        role: payload.role.toUpperCase(),
        phone: payload.phone || "",
      }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Registration failed");
    }
    const data: TokenResponse = await res.json();
    localStorage.setItem("token", data.access_token);
    localStorage.setItem("user_role", data.role);
    localStorage.setItem("user_name", data.full_name);
    return data;
  },

  logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("user_role");
    localStorage.removeItem("user_name");
  },

  async getProfile(): Promise<UserResponse> {
    const res = await fetch(apiUrl("/api/auth/me"), {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Could not fetch profile");
    return res.json();
  },

  // Shipments
  async listShipments(): Promise<Shipment[]> {
    const res = await fetch(apiUrl("/api/shipments"), { headers: getAuthHeaders() });
    if (!res.ok) throw new Error("Failed to load shipments");
    const data = await res.json();
    return data.shipments;
  },

  async getShipment(code: string): Promise<any> {
    const res = await fetch(apiUrl(`/api/shipments/${code}`), { headers: getAuthHeaders() });
    if (!res.ok) throw new Error("Failed to load shipment details");
    return res.json();
  },

  // Products
  async listProducts(): Promise<ProductProfile[]> {
    const res = await fetch(apiUrl("/api/products"), { headers: getAuthHeaders() });
    if (!res.ok) throw new Error("Failed to load products");
    const data = await res.json();
    return data.products;
  },

  // Interventions
  async simulate(code: string): Promise<WhatIfSimulationResponse> {
    const res = await fetch(apiUrl(`/api/interventions/${code}/simulate`), {
      method: "POST",
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to simulate what-if scenarios");
    return res.json();
  },

  async approve(code: string): Promise<any> {
    const res = await fetch(apiUrl(`/api/interventions/${code}/approve`), {
      method: "POST",
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to approve recommendation");
    return res.json();
  },

  async override(code: string, reason: string): Promise<any> {
    const res = await fetch(apiUrl(`/api/interventions/${code}/override`), {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ overrideReason: reason }),
    });
    if (!res.ok) throw new Error("Failed to override recommendation");
    return res.json();
  },

  async fieldAccept(code: string): Promise<any> {
    const res = await fetch(apiUrl(`/api/interventions/${code}/field-accept`), {
      method: "POST",
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to accept route");
    return res.json();
  },

  async toggleBackupCooling(code: string): Promise<any> {
    const res = await fetch(apiUrl(`/api/interventions/${code}/backup-cooling`), {
      method: "POST",
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to toggle backup cooling");
    return res.json();
  },

  async confirmHandoff(code: string, photoUrl?: string): Promise<any> {
    const res = await fetch(apiUrl(`/api/interventions/${code}/handoff`), {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ handoffPhotoUrl: photoUrl || "" }),
    });
    if (!res.ok) throw new Error("Failed to confirm handoff");
    return res.json();
  },

  // WebSockets
  connectTelemetry(onMessage: (data: any) => void): WebSocket {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const configuredWsUrl = import.meta.env.VITE_WS_URL as string | undefined;
    const socket = new WebSocket(configuredWsUrl || `${protocol}//${window.location.host}/ws`);
    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        onMessage(payload);
      } catch (err) {
        console.error("Error parsing telemetry WebSocket frame:", err);
      }
    };
    return socket;
  },
};
