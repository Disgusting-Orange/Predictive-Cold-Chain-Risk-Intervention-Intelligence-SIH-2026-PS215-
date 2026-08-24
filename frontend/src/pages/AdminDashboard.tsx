/**
 * Operations workspace design: a practical, restrained control-room interface with flat surfaces, clear hierarchy, and functional task navigation.
 */
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  Bell,
  Check,
  ChevronDown,
  CircleAlert,
  ClipboardCheck,
  FileDown,
  Filter,
  Globe,
  HardDrive,
  LayoutDashboard,
  LogOut,
  MapPin,
  Menu,
  PackageSearch,
  Plus,
  RefreshCw,
  Route,
  Search,
  Settings2,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  ThermometerSun,
  Truck,
  Wifi,
  WifiOff,
  X,
} from "lucide-react";
import { useMemo, useState, useEffect, type ReactNode } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Link, useLocation } from "wouter";
import { api } from "../lib/api";

const tempData = [
  { time: "08:00", temperature: 4.3 }, { time: "08:30", temperature: 4.8 }, { time: "09:00", temperature: 5.2 }, { time: "09:30", temperature: 6.1 }, { time: "10:00", temperature: 6.7 }, { time: "10:30", temperature: 7.4 }, { time: "11:00", temperature: 8.2 },
];

export type ShipmentStatus = "High" | "Attention" | "Safe";

export interface Shipment {
  id: string;
  product: string;
  batch: string;
  origin: string;
  destination: string;
  status: ShipmentStatus;
  healthScore: number;
  risk: number;
  temperature: string;
  eta: string;
  safeLife: string;
  x: string;
  y: string;
}

const defaultShipments: Shipment[] = [
  { id: "SHP-1042", product: "Milk", batch: "M102", origin: "MediCold Distribution Centre", destination: "Apollo Hospital Pharmacy", status: "High", healthScore: 28, risk: 72, temperature: "8.2°C", eta: "42 min", safeLife: "38 min", x: "52%", y: "45%" },
  { id: "SHP-1041", product: "Vaccines", batch: "V001", origin: "Serum Institute Pune", destination: "Rajiv Gandhi Hospital Chennai", status: "Safe", healthScore: 98, risk: 2, temperature: "4.1°C", eta: "68 min", safeLife: "320 min", x: "42%", y: "14%" },
  { id: "SHP-1043", product: "Insulin", batch: "I509", origin: "Biotech Hub Bangalore", destination: "City Care Clinic Coimbatore", status: "Attention", healthScore: 65, risk: 35, temperature: "6.8°C", eta: "115 min", safeLife: "140 min", x: "82%", y: "70%" },
];

type Workspace = "Dashboard" | "Live Shipments" | "Risk Monitor" | "Recommended Actions" | "Route Planning" | "Product Profiles" | "Audit Reports";

function Panel({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <article className={`relative overflow-hidden border border-slate-800 bg-[#101820] before:absolute before:left-0 before:top-0 before:h-px before:w-9 before:bg-[#278a69] ${className}`}>{children}</article>;
}

function RiskBadge({ status }: { status: Shipment["status"] }) {
  const styles = status === "High" ? "border-[#6e3c3b] bg-[#281819] text-[#e9918d]" : status === "Attention" ? "border-[#655129] bg-[#272115] text-[#e4c177]" : "border-[#315a48] bg-[#16271f] text-[#78c8a5]";
  return <span className={`inline-flex rounded border px-2 py-1 text-[10px] font-bold uppercase tracking-[0.08em] ${styles}`}>{status}</span>;
}

const navItems = [
  ["Dashboard", LayoutDashboard], ["Live Shipments", Truck], ["Risk Monitor", CircleAlert], ["Recommended Actions", ClipboardCheck], ["Route Planning", Route], ["Product Profiles", PackageSearch], ["Audit Reports", FileDown],
] as const;

function MiniMap({ shipments, selected, onSelect }: { shipments: Shipment[]; selected: Shipment; onSelect: (shipment: Shipment) => void }) {
  const colorFor = (status: Shipment["status"]) => status === "High" ? "#d56560" : status === "Attention" ? "#d6a855" : "#26986f";
  return (
    <div className="relative mt-4 h-[285px] overflow-hidden border border-slate-800 bg-[#111f24]" aria-label="Shipment route map">
      <div className="absolute left-[10%] top-[57%] h-px w-[74%] -rotate-[26deg] bg-[#239b75]/70" />
      <div className="absolute left-[21%] top-[34%] h-px w-[45%] rotate-[17deg] bg-slate-600/60" />
      <div className="absolute -left-12 top-8 h-44 w-[72%] rotate-[-18deg] rounded-full border-[22px] border-[#1a3030]" />
      <div className="absolute right-[-80px] bottom-[-44px] h-60 w-[47%] rotate-[20deg] rounded-full border-[22px] border-[#192931]" />
      <span className="absolute left-4 bottom-4 text-[10px] font-bold tracking-[0.1em] text-slate-500">BENGALURU / 01</span>
      <span className="absolute right-4 top-4 text-[10px] font-bold tracking-[0.1em] text-slate-500">CHENNAI / 02</span>
      {[["18%", "22%"], ["42%", "14%"], ["58%", "76%"], ["88%", "46%"], ["37%", "83%"]].map(([left, top]) => (
        <span key={`${left}-${top}`} className="absolute h-1.5 w-1.5 rounded-full bg-[#6ed8b2] opacity-70" style={{ left, top, boxShadow: "0 0 0 3px rgba(39,139,105,0.12)" }} />
      ))}
      {shipments.map((shipment) => (
        <button
          type="button"
          key={shipment.id}
          onClick={() => onSelect(shipment)}
          style={{ left: shipment.x, top: shipment.y, borderColor: colorFor(shipment.status) }}
          className={`absolute grid h-9 w-9 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full border-2 bg-[#101820] transition hover:scale-110 ${selected.id === shipment.id ? "ring-2 ring-white/60 scale-110" : ""}`}
          title={`Select ${shipment.id}`}
        >
          <Truck className="h-3.5 w-3.5" style={{ color: colorFor(shipment.status) }} />
        </button>
      ))}
    </div>
  );
}

export default function AdminDashboard() {
  const [, setLocation] = useLocation();
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const handleSignOut = () => { localStorage.removeItem("token"); setLocation("/login"); };
  const [mobileNav, setMobileNav] = useState(false);
  const [activeView, setActiveView] = useState<Workspace>("Dashboard");
  const [shipments, setShipments] = useState<Shipment[]>(defaultShipments);
  const [selectedShipment, setSelectedShipment] = useState<Shipment>(defaultShipments[0]);
  const [productsList, setProductsList] = useState<any[]>([]);
  const [simulationScenarios, setSimulationScenarios] = useState<any[]>([]);
  const [auditTrail, setAuditTrail] = useState<any[]>([]);
  const [edgeStatus, setEdgeStatus] = useState<any>({ mode: "ONLINE", queue_size: 0 });
  const [isSimulatingOffline, setIsSimulatingOffline] = useState(false);
  
  const [liveDetailOpen, setLiveDetailOpen] = useState(false);
  const [shipmentFilter, setShipmentFilter] = useState<"All" | Shipment["status"]>("All");
  const [searchTerm, setSearchTerm] = useState("");
  const [simulatorOpen, setSimulatorOpen] = useState(false);
  const [overrideOpen, setOverrideOpen] = useState(false);
  const [reportGenerated, setReportGenerated] = useState(false);
  const [pendingActions, setPendingActions] = useState([
    { id: "SHP-1042", action: "Reroute to Cold Storage A (Guindy)", reason: "Safe life is under 45 minutes", status: "High" as const }
  ]);

  const mapBackendShipment = (s: any): Shipment => {
    const statusMap: Record<string, "High" | "Attention" | "Safe"> = {
      CRITICAL: "High",
      DIVERTED: "Attention",
      DELIVERED: "Safe",
      IN_TRANSIT: s.riskScore > 70 ? "High" : s.riskScore > 30 ? "Attention" : "Safe"
    };
    return {
      id: s.shipmentId,
      product: s.productName,
      batch: s.shipmentId.replace("SHP-", "B-"),
      origin: s.origin.name,
      destination: s.destination.name,
      status: statusMap[s.status] || "Safe",
      healthScore: Math.max(0, 100 - s.riskScore),
      risk: s.riskScore,
      temperature: `${s.temperature.toFixed(1)}°C`,
      eta: `${s.etaMinutes} min`,
      safeLife: s.remainingSafeLifeMinutes ? `${s.remainingSafeLifeMinutes} min` : "N/A",
      x: s.shipmentId === "SHP-1041" ? "42%" : s.shipmentId === "SHP-1042" ? "52%" : "82%",
      y: s.shipmentId === "SHP-1041" ? "14%" : s.shipmentId === "SHP-1042" ? "45%" : "70%",
    };
  };

  const loadData = async () => {
    try {
      const active = await api.listShipments();
      const mapped = active.map(mapBackendShipment);
      if (mapped.length > 0) {
        setShipments(mapped);
        setSelectedShipment(prev => {
          const updated = mapped.find(m => m.id === prev.id);
          return updated || mapped[0];
        });
      }
      
      const prods = await api.listProducts();
      setProductsList(prods);

      const edge = await api.getEdgeStatus();
      setEdgeStatus(edge);
      setIsSimulatingOffline(edge.mode === "LOCAL_ONLY");
    } catch (err) {
      console.error("Failed to load initial data", err);
    }
  };

  const loadAuditTrail = async (shipmentId: string) => {
    try {
      const res = await api.getAuditTrail(shipmentId);
      if (res && res.auditTrail) {
        setAuditTrail(res.auditTrail);
      }
    } catch (err) {
      console.error("Failed to load audit trail", err);
    }
  };

  useEffect(() => {
    loadData();
    const ws = api.connectTelemetry((msg) => {
      if (msg.type === "TELEMETRY_UPDATE" || msg.type === "DEMO_STATE") {
        loadData();
      }
    });
    return () => ws.close();
  }, []);

  useEffect(() => {
    if (selectedShipment) {
      api.simulate(selectedShipment.id)
        .then(res => setSimulationScenarios(res.scenarios))
        .catch(err => console.error("Simulation failed", err));
      loadAuditTrail(selectedShipment.id);
    }
  }, [selectedShipment]);

  const toggleEdgeNetwork = async () => {
    try {
      const nextOnline = isSimulatingOffline; // if currently offline, set online
      const res = await api.simulateNetwork(nextOnline);
      setIsSimulatingOffline(!nextOnline);
      setEdgeStatus(res);
      loadData();
    } catch (err: any) {
      alert("Failed to toggle edge network simulation: " + err.message);
    }
  };

  const filteredShipments = useMemo(() => shipments.filter((shipment) => {
    const matchesFilter = shipmentFilter === "All" || shipment.status === shipmentFilter;
    const terms = `${shipment.id} ${shipment.product} ${shipment.origin} ${shipment.destination}`.toLowerCase();
    return matchesFilter && terms.includes(searchTerm.toLowerCase());
  }), [shipments, shipmentFilter, searchTerm]);

  const selectShipment = (shipment: Shipment) => {
    setSelectedShipment(shipment);
    setLiveDetailOpen(true);
  };

  const changeView = (view: Workspace) => {
    setActiveView(view);
    setMobileNav(false);
  };

  const approveAction = async (id: string) => {
    try {
      await api.approve(id);
      setPendingActions((items) => items.filter((item) => item.id !== id));
      loadData();
    } catch (err: any) {
      alert("Approve failed: " + err.message);
    }
  };

  const overrideAction = async (id: string, reason: string) => {
    try {
      await api.override(id, reason);
      setPendingActions((items) => items.filter((item) => item.id !== id));
      setOverrideOpen(false);
      loadData();
    } catch (err: any) {
      alert("Override failed: " + err.message);
    }
  };

  const viewMeta: Record<Workspace, { eyebrow: string; title: string; description: string }> = {
    Dashboard: { eyebrow: "OPERATIONS", title: "Operations overview", description: "Live visibility across active cold-chain shipments and AI edge predictions." },
    "Live Shipments": { eyebrow: "LIVE SHIPMENTS", title: "Active shipments", description: "Search, filter, and inspect shipment telemetry in real time." },
    "Risk Monitor": { eyebrow: "RISK MONITOR", title: "Shipment health & TreeSHAP", description: "Review temperature exposure, SHAP attribution factors, and remaining safe life." },
    "Recommended Actions": { eyebrow: "ACTION QUEUE", title: "Recommended actions", description: "Review AI What-If interventions requiring human confirmation." },
    "Route Planning": { eyebrow: "ROUTE PLANNING", title: "Intervention comparison", description: "Compare 3-candidate routing scenarios before dispatching changes." },
    "Product Profiles": { eyebrow: "PRODUCT PROFILES", title: "Temperature profiles", description: "Configure temperature corridors and sensitivity thresholds for monitored cargo." },
    "Audit Reports": { eyebrow: "AUDIT REPORTS", title: "Compliance & decision trail", description: "Review timestamped telemetry events, XGBoost risk assessments, and approvals." },
  };
  const meta = viewMeta[activeView];

  return (
    <main className="min-h-screen bg-[#0b1117] font-sans text-slate-200">
      {/* Header */}
      <header className="sticky top-0 z-40 flex h-[64px] items-center justify-between border-b border-slate-800 bg-[#0d151d] px-4 sm:px-6">
        <div className="flex items-center gap-3">
          <button type="button" onClick={() => setMobileNav(!mobileNav)} className="grid h-9 w-9 place-items-center rounded border border-slate-700 text-slate-300 lg:hidden">
            <Menu className="h-4 w-4" />
          </button>
          <Link href="/" className="flex items-center gap-2.5">
            <img src="/manus-storage/cold-chain-mark_8a9c38e3.png" alt="Cold Chain AI" className="h-8 w-8" />
            <div>
              <p className="font-display text-[13px] font-bold uppercase tracking-[0.12em] text-white">Cold Chain <span className="text-[#73c8a7]">AI</span></p>
              <p className="text-[8px] font-bold uppercase tracking-[0.2em] text-slate-500">Ops / Control</p>
            </div>
          </Link>
        </div>

        {/* Search */}
        <label className="relative hidden w-full max-w-sm md:block">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input value={searchTerm} onChange={(event) => setSearchTerm(event.target.value)} className="h-9 w-full rounded border border-slate-700 bg-[#111b24] pl-9 pr-3 text-sm text-white outline-none placeholder:text-slate-600 focus:border-[#278a69]" placeholder="Search shipments or products" />
        </label>

        {/* Controls / Edge Simulator / User */}
        <div className="flex items-center gap-2.5">
          {/* Edge Network Mode Toggle */}
          <button
            type="button"
            onClick={toggleEdgeNetwork}
            title={isSimulatingOffline ? "Local Edge Gateway running offline (Click to restore Internet)" : "Connected to Cloud (Click to test Offline Edge ML)"}
            className={`flex items-center gap-2 rounded border px-2.5 py-1.5 text-xs font-semibold transition ${isSimulatingOffline ? "border-amber-600/60 bg-amber-950/40 text-amber-300 hover:bg-amber-900/50" : "border-[#278a69]/60 bg-[#133329] text-[#8ad8bb] hover:bg-[#1a4034]"}`}
          >
            {isSimulatingOffline ? <WifiOff className="h-3.5 w-3.5 text-amber-400" /> : <Wifi className="h-3.5 w-3.5 text-[#73c8a7]" />}
            <span className="hidden sm:inline">{isSimulatingOffline ? "Edge: LOCAL ONLY" : "Edge: ONLINE"}</span>
          </button>

          <div className="relative">
            <button type="button" onClick={() => setUserMenuOpen(!userMenuOpen)} className="flex items-center gap-2 rounded border border-slate-700 bg-[#111b24] px-2.5 py-1.5">
              <span className="grid h-6 w-6 place-items-center rounded bg-[#238767] text-[9px] font-bold text-white">AM</span>
              <span className="hidden text-xs font-semibold text-slate-300 sm:block">Operations Admin</span>
              <ChevronDown className={`hidden h-3 w-3 text-slate-500 transition-transform sm:block ${userMenuOpen ? "rotate-180" : ""}`} />
            </button>
            {userMenuOpen && (
              <div className="absolute right-0 top-full z-50 mt-1 w-56 border border-slate-700 bg-[#111b24] shadow-xl">
                <div className="border-b border-slate-700 px-4 py-3">
                  <p className="text-xs font-semibold text-white">Fleet Operations Admin</p>
                  <p className="mt-0.5 text-[10px] text-slate-500">admin@coldchain.ai</p>
                </div>
                <Link href="/field-agent" className="flex items-center gap-2 px-4 py-2.5 text-xs text-slate-300 hover:bg-slate-800 hover:text-white">
                  <Truck className="h-3.5 w-3.5 text-[#74c8a7]" /> Switch to Field Driver Cockpit
                </Link>
                <Link href="/client" className="flex items-center gap-2 px-4 py-2.5 text-xs text-slate-300 hover:bg-slate-800 hover:text-white">
                  <Activity className="h-3.5 w-3.5 text-[#74c8a7]" /> Switch to Client Pharmacy View
                </Link>
                <button type="button" onClick={handleSignOut} className="flex w-full items-center gap-2 border-t border-slate-800 px-4 py-2.5 text-left text-xs text-rose-400 hover:bg-slate-800">
                  <LogOut className="h-3.5 w-3.5" /> Sign out
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Grid */}
      <div className="flex">
        {/* Sidebar */}
        <aside className={`${mobileNav ? "fixed inset-x-0 top-[64px] z-30 block border-b border-slate-800" : "hidden"} w-full shrink-0 bg-[#0d151d] p-3 lg:sticky lg:top-[64px] lg:block lg:h-[calc(100vh-64px)] lg:w-[230px] lg:border-b-0 lg:border-r lg:border-slate-800`}>
          <p className="mb-3 px-3 text-[10px] font-bold uppercase tracking-[0.12em] text-slate-500">Operations</p>
          <nav className="space-y-1">
            {navItems.map(([label, NavIcon]) => {
              const Icon = NavIcon;
              const selected = activeView === label;
              return (
                <button
                  type="button"
                  key={label}
                  onClick={() => changeView(label)}
                  className={`flex min-h-10 w-full items-center gap-3 rounded px-3 text-left text-sm font-medium transition ${selected ? "bg-[#18362d] text-[#7bd0af] font-semibold" : "text-slate-400 hover:bg-slate-800/70 hover:text-slate-100"}`}
                >
                  <Icon className="h-4 w-4" /> {label}
                </button>
              );
            })}
          </nav>
          
          <div className="mt-6 border-t border-slate-800 pt-4">
            <p className="mb-2 px-3 text-[10px] font-bold uppercase tracking-[0.12em] text-slate-500">Quick Workspaces</p>
            <Link href="/field-agent" className="flex min-h-9 w-full items-center gap-2 rounded px-3 text-xs text-slate-400 hover:bg-slate-800 hover:text-slate-200">
              <Truck className="h-3.5 w-3.5" /> Field Driver View
            </Link>
            <Link href="/client" className="flex min-h-9 w-full items-center gap-2 rounded px-3 text-xs text-slate-400 hover:bg-slate-800 hover:text-slate-200">
              <Activity className="h-3.5 w-3.5" /> Pharmacy Client View
            </Link>
          </div>
        </aside>

        {/* View Content */}
        <section className="min-w-0 flex-1 p-4 sm:p-6 lg:p-8">
          <div className="mx-auto max-w-[1480px]">
            {/* View Header */}
            <div className="flex flex-col justify-between gap-4 border-b border-slate-800 pb-5 sm:flex-row sm:items-end">
              <div>
                <div className="flex items-center gap-3">
                  <span className="h-px w-8 bg-[#278a69]" />
                  <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#68bfa0]">{meta.eyebrow}</p>
                </div>
                <h1 className="font-display mt-3 text-4xl font-bold tracking-[-0.055em] text-white">{meta.title}</h1>
                <p className="mt-2 text-sm text-slate-400">{meta.description}</p>
              </div>
              <div className="flex items-center gap-3">
                <div className="hidden border-l border-slate-800 pl-4 text-right sm:block">
                  <p className="text-[10px] font-bold uppercase tracking-[0.1em] text-slate-500">AI Engine</p>
                  <p className="mt-1 flex items-center justify-end gap-2 text-xs font-semibold text-[#74c8a7]">
                    <span className="h-2 w-2 rounded-full bg-[#278a69] animate-pulse" /> XGBoost V2 (40 Features)
                  </p>
                </div>
                {activeView === "Dashboard" && (
                  <button type="button" onClick={() => setSimulatorOpen(!simulatorOpen)} className="min-h-10 rounded border border-[#2e7660] bg-[#133329] px-4 text-sm font-semibold text-[#8ad8bb] hover:bg-[#1a4034]">
                    {simulatorOpen ? "Hide route comparison" : "Compare routes"}
                  </button>
                )}
              </div>
            </div>

            {/* 1. DASHBOARD VIEW */}
            {activeView === "Dashboard" && (
              <>
                <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                  {[
                    ["Active shipments", shipments.length.toString(), "all live loads", Truck],
                    ["High risk", shipments.filter(s => s.status === "High").length.toString(), "needs review", CircleAlert],
                    ["Attention", shipments.filter(s => s.status === "Attention").length.toString(), "watch closely", Activity],
                    ["Safe", shipments.filter(s => s.status === "Safe").length.toString(), "within range", ShieldCheck],
                  ].map(([label, value, note, StatIcon], index) => {
                    const Icon = StatIcon as typeof Truck;
                    const color = index === 1 ? "text-[#e9918d]" : index === 2 ? "text-[#e4c177]" : "text-[#72c8a5]";
                    return (
                      <Panel key={label as string} className="p-4">
                        <div className="flex items-center justify-between">
                          <p className="text-xs font-medium text-slate-400">{label as string}</p>
                          <Icon className={`h-4 w-4 ${color}`} />
                        </div>
                        <p className="font-display mt-4 text-4xl font-bold tracking-[-0.065em] text-white">{value as string}</p>
                        <p className="mt-1 text-xs text-slate-500">{note as string}</p>
                      </Panel>
                    );
                  })}
                </div>

                <div className="mt-5 grid gap-5 xl:grid-cols-[1.12fr_0.88fr]">
                  <Panel className="p-5">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-xs font-semibold text-slate-300">Live shipment fleet map</p>
                        <p className="mt-1 text-sm text-slate-500">Click any marker to select and inspect.</p>
                      </div>
                      <span className="text-xs font-semibold text-[#73c6a7]">{shipments.length} active</span>
                    </div>
                    <MiniMap shipments={shipments} selected={selectedShipment} onSelect={selectShipment} />
                    <div className="mt-3 flex gap-4 text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-500">
                      <span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-[#d56560]" />High</span>
                      <span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-[#d6a855]" />Attention</span>
                      <span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-[#26986f]" />Safe</span>
                    </div>
                  </Panel>

                  <Panel className="p-5">
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="text-xs font-semibold text-slate-400">Selected shipment</p>
                        <h2 className="font-display mt-1 text-3xl font-bold tracking-[-0.06em] text-white">{selectedShipment.id}</h2>
                        <p className="mt-1 text-sm text-slate-500">{selectedShipment.product} · Batch {selectedShipment.batch}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <RiskBadge status={selectedShipment.status} />
                        <Link href={`/shipment/${selectedShipment.id}`} className="rounded border border-slate-700 bg-slate-800/80 p-1.5 text-slate-300 hover:text-white" title="Open full deep-dive page">
                          <ArrowUpRight className="h-4 w-4" />
                        </Link>
                      </div>
                    </div>
                    <div className="mt-5 grid grid-cols-2 gap-x-5 gap-y-4 border-y border-slate-800 py-4 text-sm">
                      <div>
                        <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-slate-500">Origin</p>
                        <p className="mt-1 font-medium text-slate-200">{selectedShipment.origin}</p>
                      </div>
                      <div>
                        <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-slate-500">Destination</p>
                        <p className="mt-1 font-medium text-slate-200">{selectedShipment.destination}</p>
                      </div>
                      <div>
                        <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-slate-500">ETA</p>
                        <p className="mt-1 font-medium text-slate-200">{selectedShipment.eta}</p>
                      </div>
                      <div>
                        <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-slate-500">Temperature</p>
                        <p className="mt-1 font-medium text-slate-200">{selectedShipment.temperature}</p>
                      </div>
                    </div>
                    <div className="mt-5 grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-xs text-slate-500">Spoilage risk</p>
                        <p className="font-display mt-1 text-4xl font-bold tracking-[-0.07em] text-[#e9918d]">{selectedShipment.risk}%</p>
                      </div>
                      <div>
                        <p className="text-xs text-slate-500">Safe life remaining</p>
                        <p className="font-display mt-1 text-4xl font-bold tracking-[-0.07em] text-white">{selectedShipment.safeLife}</p>
                      </div>
                    </div>
                  </Panel>
                </div>

                <div className="mt-5 grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
                  <Panel className="p-5">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-xs font-semibold text-slate-300">Temperature telemetry history</p>
                        <p className="mt-1 text-sm text-slate-500">{selectedShipment.product} · {selectedShipment.id}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-slate-500">Current</p>
                        <p className="mt-1 text-xl font-semibold text-[#e9918d]">{selectedShipment.temperature}</p>
                      </div>
                    </div>
                    <div className="mt-4 h-[220px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={tempData} margin={{ top: 6, right: 8, left: -20, bottom: 0 }}>
                          <CartesianGrid stroke="#ffffff12" vertical={false} />
                          <XAxis dataKey="time" tick={{ fill: "#718095", fontSize: 11 }} axisLine={false} tickLine={false} />
                          <YAxis domain={[0, 10]} tick={{ fill: "#718095", fontSize: 11 }} axisLine={false} tickLine={false} />
                          <Tooltip contentStyle={{ background: "#101820", border: "1px solid #334155", borderRadius: 4 }} labelStyle={{ color: "#cbd5e1" }} itemStyle={{ color: "#f09a93" }} />
                          <Line type="monotone" dataKey="temperature" stroke="#df716b" strokeWidth={2.5} dot={{ r: 2.5, fill: "#df716b" }} />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-4 border-t border-slate-800 pt-3 text-xs">
                      <span className="text-slate-500">Safe range: <b className="ml-1 text-[#74c8a7]">2–6°C</b></span>
                      <span className="text-slate-500">Above range: <b className="ml-1 text-[#e9918d]">21 min</b></span>
                      <span className="text-slate-500">Risk Fusion: <b className="ml-1 text-[#e9918d]">{selectedShipment.risk > 50 ? "PREDICTED_RISK" : "SAFE"}</b></span>
                    </div>
                  </Panel>

                  <Panel className="p-5">
                    <p className="text-xs font-semibold text-slate-300">TreeSHAP Risk Factor Attribution</p>
                    <p className="mt-1 text-sm text-slate-500">Key causal variables driving XGBoost risk score.</p>
                    <ul className="mt-5 space-y-3">
                      {[
                        { factor: "spatial_range_t", label: "Multi-probe temperature gradient (> 3.2°C)", impact: "+34% risk" },
                        { factor: "rolling_mean_30m", label: "30-min warming velocity exceeds threshold", impact: "+26% risk" },
                        { factor: "ambient_delta", label: "Ambient exterior thermal exposure high (36°C)", impact: "+18% risk" },
                        { factor: "battery_reserve", label: "Auxiliary cooling power stable (88%)", impact: "-6% risk" },
                      ].map((item) => (
                        <li key={item.factor} className="flex items-center justify-between text-xs text-slate-300">
                          <span className="flex items-center gap-2">
                            <span className="h-1.5 w-1.5 rounded-full bg-[#d6a855]" />
                            {item.label}
                          </span>
                          <span className="font-mono font-semibold text-slate-400">{item.impact}</span>
                        </li>
                      ))}
                    </ul>
                    <div className="mt-6 border-t border-slate-800 pt-4">
                      <p className="text-xs font-semibold text-slate-300">AI Suggested Action</p>
                      <p className="mt-1 text-lg font-semibold text-white">Reroute to Cold Storage A (Guindy)</p>
                      <div className="mt-4 grid gap-2 sm:grid-cols-3">
                        <button type="button" onClick={() => approveAction(selectedShipment.id)} className="min-h-10 rounded bg-[#238767] px-3 text-xs font-semibold text-white hover:bg-[#2c9c78]">
                          Approve
                        </button>
                        <button type="button" onClick={() => setActiveView("Route Planning")} className="min-h-10 rounded border border-slate-700 px-3 text-xs font-semibold text-slate-200 hover:bg-slate-800">
                          Alternatives
                        </button>
                        <button type="button" onClick={() => setOverrideOpen(!overrideOpen)} className="min-h-10 rounded border border-slate-700 px-3 text-xs font-semibold text-slate-200 hover:bg-slate-800">
                          Override
                        </button>
                      </div>
                      {overrideOpen && (
                        <select onChange={(e) => overrideAction(selectedShipment.id, e.target.value)} className="mt-3 h-10 w-full rounded border border-slate-700 bg-[#111b24] px-3 text-xs text-slate-200">
                          <option>Select override reason</option>
                          <option value="Driver verified secondary thermometer">Driver verified secondary thermometer</option>
                          <option value="Cold storage A capacity full">Cold storage A capacity full</option>
                          <option value="Customer priority expedite">Customer priority expedite</option>
                          <option value="Other">Other</option>
                        </select>
                      )}
                    </div>
                  </Panel>
                </div>

                {simulatorOpen && (
                  <Panel className="mt-5 p-5">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-xs font-semibold text-slate-300">What-If Route Comparison Matrix</p>
                        <p className="mt-1 text-sm text-slate-500">Projected risk outcomes for {selectedShipment.id}.</p>
                      </div>
                      <button type="button" onClick={() => setSimulatorOpen(false)} className="text-xs font-semibold text-slate-500 hover:text-white">
                        <X className="inline h-3.5 w-3.5" /> Close
                      </button>
                    </div>
                    <div className="mt-4 grid gap-3 lg:grid-cols-3">
                      {(simulationScenarios.length > 0 ? simulationScenarios : [
                        { scenarioName: "Continue Current Route", projectedRiskScore: 72, projectedEtaMinutes: 38, projectedLossAvoided: 0, isRecommended: false },
                        { scenarioName: "Reroute to Cold Storage A", projectedRiskScore: 14, projectedEtaMinutes: 22, projectedLossAvoided: 185000, isRecommended: true },
                        { scenarioName: "Emergency Expedited Delivery", projectedRiskScore: 28, projectedEtaMinutes: 30, projectedLossAvoided: 95000, isRecommended: false }
                      ]).map((s: any) => (
                        <div key={s.scenarioName} className={`border p-4 ${s.isRecommended ? "border-[#318368] bg-[#14261f]" : "border-slate-800 bg-[#0d161e]"}`}>
                          <div className="flex items-start justify-between gap-3">
                            <p className="text-sm font-semibold text-white">{s.scenarioName}</p>
                            {s.isRecommended && <span className="text-[10px] font-bold uppercase tracking-[0.08em] text-[#7bd0af]">Preferred</span>}
                          </div>
                          <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
                            <div>
                              <p className="text-slate-500">Risk</p>
                              <p className="mt-1 font-semibold text-white">{s.projectedRiskScore}%</p>
                            </div>
                            <div>
                              <p className="text-slate-500">ETA</p>
                              <p className="mt-1 font-semibold text-white">{s.projectedEtaMinutes} min</p>
                            </div>
                            <div>
                              <p className="text-slate-500">Loss Avoided</p>
                              <p className="mt-1 font-semibold text-[#74c8a7]">₹{s.projectedLossAvoided.toLocaleString()}</p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </Panel>
                )}
              </>
            )}

            {/* 2. LIVE SHIPMENTS VIEW */}
            {activeView === "Live Shipments" && (
              <>
                <Panel className="mt-5 p-4">
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                    <label className="relative block max-w-xl flex-1">
                      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                      <input value={searchTerm} onChange={(event) => setSearchTerm(event.target.value)} className="h-10 w-full rounded border border-slate-700 bg-[#0d161e] pl-9 pr-3 text-sm text-white outline-none placeholder:text-slate-600 focus:border-[#278a69]" placeholder="Search by shipment, product, or destination" />
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {(["All", "High", "Attention", "Safe"] as const).map((filter) => (
                        <button type="button" key={filter} onClick={() => setShipmentFilter(filter)} className={`min-h-9 rounded border px-3 text-xs font-semibold ${shipmentFilter === filter ? "border-[#2d7660] bg-[#17362c] text-[#82d1b0]" : "border-slate-700 text-slate-400 hover:bg-slate-800"}`}>
                          {filter === "All" ? "All shipments" : filter}
                        </button>
                      ))}
                    </div>
                  </div>
                </Panel>

                <div className="mt-5 grid gap-5 xl:grid-cols-[1fr_0.68fr]">
                  <Panel className="overflow-hidden">
                    <div className="border-b border-slate-800 px-5 py-4 flex items-center justify-between">
                      <div>
                        <p className="text-sm font-semibold text-white">{filteredShipments.length} Active Shipments</p>
                        <p className="mt-1 text-xs text-slate-500">Select any row to inspect telemetry & AI risk scores.</p>
                      </div>
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full min-w-[680px] text-left text-sm">
                        <thead className="border-b border-slate-800 bg-[#0d161e] text-[10px] font-bold uppercase tracking-[0.08em] text-slate-500">
                          <tr>
                            <th className="px-5 py-3">Shipment</th>
                            <th className="px-5 py-3">Route</th>
                            <th className="px-5 py-3">Temperature</th>
                            <th className="px-5 py-3">ETA</th>
                            <th className="px-5 py-3">Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {filteredShipments.map((shipment) => (
                            <tr key={shipment.id} onClick={() => selectShipment(shipment)} className={`cursor-pointer border-b border-slate-800/80 text-slate-300 transition hover:bg-slate-800/50 ${selectedShipment.id === shipment.id ? "bg-[#14261f]" : ""}`}>
                              <td className="px-5 py-4">
                                <p className="font-semibold text-white">{shipment.id}</p>
                                <p className="mt-1 text-xs text-slate-500">{shipment.product} · {shipment.batch}</p>
                              </td>
                              <td className="px-5 py-4 text-xs">
                                <p>{shipment.origin}</p>
                                <p className="mt-1 text-slate-500">to {shipment.destination}</p>
                              </td>
                              <td className="px-5 py-4">
                                <p className="font-medium text-white">{shipment.temperature}</p>
                                <p className="mt-1 text-xs text-slate-500">Safe life: {shipment.safeLife}</p>
                              </td>
                              <td className="px-5 py-4 font-medium">{shipment.eta}</td>
                              <td className="px-5 py-4"><RiskBadge status={shipment.status} /></td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </Panel>

                  {/* Selected Shipment Summary Card */}
                  <Panel className="p-5">
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="text-xs font-semibold text-slate-400">Selected Cargo Record</p>
                        <h3 className="font-display mt-1 text-2xl font-bold text-white">{selectedShipment.id}</h3>
                        <p className="mt-1 text-xs text-slate-500">{selectedShipment.product} · {selectedShipment.origin} → {selectedShipment.destination}</p>
                      </div>
                      <RiskBadge status={selectedShipment.status} />
                    </div>

                    <div className="mt-5 space-y-3 border-y border-slate-800 py-4 text-xs">
                      <div className="flex justify-between"><span className="text-slate-500">Health Score:</span><span className="font-semibold text-white">{selectedShipment.healthScore}/100</span></div>
                      <div className="flex justify-between"><span className="text-slate-500">Spoilage Probability:</span><span className="font-semibold text-[#e9918d]">{selectedShipment.risk}%</span></div>
                      <div className="flex justify-between"><span className="text-slate-500">Remaining Safe Life:</span><span className="font-semibold text-white">{selectedShipment.safeLife}</span></div>
                      <div className="flex justify-between"><span className="text-slate-500">Current Reading:</span><span className="font-semibold text-white">{selectedShipment.temperature}</span></div>
                    </div>

                    <div className="mt-5 flex gap-2">
                      <Link href={`/shipment/${selectedShipment.id}`} className="flex-1 rounded bg-[#238767] py-2.5 text-center text-xs font-semibold text-white hover:bg-[#2c9c78]">
                        Open Deep-Dive Page ↗
                      </Link>
                      <button type="button" onClick={() => approveAction(selectedShipment.id)} className="rounded border border-slate-700 px-3 py-2.5 text-xs font-semibold text-slate-300 hover:bg-slate-800">
                        Approve Reroute
                      </button>
                    </div>
                  </Panel>
                </div>
              </>
            )}

            {/* 3. RISK MONITOR VIEW */}
            {activeView === "Risk Monitor" && (
              <>
                <div className="mt-5 grid gap-3 sm:grid-cols-3">
                  {[
                    ["High Risk (> 70%)", shipments.filter(s => s.status === "High").length.toString(), "Immediate human intervention required", "#e9918d"],
                    ["Attention (30–70%)", shipments.filter(s => s.status === "Attention").length.toString(), "Check safe life and cooling power", "#e4c177"],
                    ["Safe (< 30%)", shipments.filter(s => s.status === "Safe").length.toString(), "Within temperature envelope", "#72c8a5"]
                  ].map(([label, count, note, color]) => (
                    <Panel key={label as string} className="p-4">
                      <p className="text-xs font-medium text-slate-400">{label as string}</p>
                      <p className="mt-3 text-3xl font-semibold" style={{ color: color as string }}>{count as string}</p>
                      <p className="mt-1 text-xs text-slate-500">{note as string}</p>
                    </Panel>
                  ))}
                </div>

                <div className="mt-5 grid gap-5 xl:grid-cols-[1fr_0.68fr]">
                  <Panel className="p-5">
                    <p className="text-sm font-semibold text-white">Priority Risk Excursions</p>
                    <p className="mt-1 text-xs text-slate-500">Sorted by XGBoost probability and safe life expiry.</p>
                    <div className="mt-4 divide-y divide-slate-800">
                      {shipments.map((s) => (
                        <div key={s.id} onClick={() => selectShipment(s)} className={`cursor-pointer grid grid-cols-[1fr_auto] gap-4 py-4 text-left transition hover:bg-slate-800/35 ${selectedShipment.id === s.id ? "bg-[#14261f] px-2 rounded" : ""}`}>
                          <div>
                            <div className="flex items-center gap-2">
                              <p className="font-semibold text-white">{s.id}</p>
                              <RiskBadge status={s.status} />
                            </div>
                            <p className="mt-1 text-xs text-slate-300">{s.product} · {s.temperature} · {s.origin} → {s.destination}</p>
                            <p className="mt-1 text-[11px] text-slate-500">Remaining safe shelf life: {s.safeLife}</p>
                          </div>
                          <div className="text-right">
                            <p className="text-2xl font-semibold text-[#e9918d]">{s.risk}%</p>
                            <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-slate-500">Risk</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </Panel>

                  <Panel className="p-5">
                    <p className="text-sm font-semibold text-white">Multi-Layer Risk Fusion Breakdown</p>
                    <p className="mt-1 text-xs text-slate-500">Synthesis of sensor health, step deltas, and XGBoost temporal model.</p>
                    <div className="mt-5 space-y-4">
                      {[
                        ["Fast Event Detector", selectedShipment.risk > 50 ? "Rapid Warming Step Detected (+0.8°C / 5min)" : "No rapid thermal anomalies", selectedShipment.risk > 50 ? "#e9918d" : "#72c8a5"],
                        ["Spatial Multi-Probe Delta", "Front-to-back gradient: 3.1°C", "#e4c177"],
                        ["Sensor Integrity", "All 9 spatial sensors online", "#72c8a5"],
                        ["Edge ML Status", edgeStatus.mode === "LOCAL_ONLY" ? "Offline Edge Gateway Running" : "Cloud Synchronized", "#72c8a5"]
                      ].map(([title, note, color]) => (
                        <div key={title as string} className="flex gap-3">
                          <span className="mt-1 h-2 w-2 shrink-0 rounded-full" style={{ background: color as string }} />
                          <div>
                            <p className="text-sm font-medium text-slate-200">{title as string}</p>
                            <p className="mt-0.5 text-xs text-slate-500">{note as string}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </Panel>
                </div>
              </>
            )}

            {/* 4. RECOMMENDED ACTIONS VIEW */}
            {activeView === "Recommended Actions" && (
              <div className="mt-5 space-y-5">
                <Panel className="p-6">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                    <div>
                      <p className="text-sm font-semibold text-white">Pending Corrective Interventions</p>
                      <p className="mt-1 text-xs text-slate-400">AI-generated response actions requiring human operator confirmation.</p>
                    </div>
                    <span className="rounded bg-[#133329] px-3 py-1 text-xs font-semibold text-[#8ad8bb]">
                      {pendingActions.length} Pending
                    </span>
                  </div>

                  <div className="mt-6 space-y-4">
                    {pendingActions.map((action) => (
                      <div key={action.id} className="rounded border border-slate-800 bg-[#0d161e] p-5">
                        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                          <div>
                            <div className="flex items-center gap-3">
                              <span className="font-display text-lg font-bold text-white">{action.id}</span>
                              <RiskBadge status={action.status} />
                              <span className="text-xs text-slate-500">Milk (Batch M102)</span>
                            </div>
                            <p className="mt-2 text-sm font-semibold text-[#74c8a7]">{action.action}</p>
                            <p className="mt-1 text-xs text-slate-400">Reason: {action.reason} · Avoids ₹1,85,000 estimated spoilage loss</p>
                          </div>

                          <div className="flex items-center gap-3">
                            <button type="button" onClick={() => approveAction(action.id)} className="rounded bg-[#238767] px-4 py-2.5 text-xs font-semibold text-white hover:bg-[#2c9c78]">
                              Approve Reroute
                            </button>
                            <button type="button" onClick={() => setOverrideOpen(true)} className="rounded border border-slate-700 px-4 py-2.5 text-xs font-semibold text-slate-300 hover:bg-slate-800">
                              Override Action
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}

                    {pendingActions.length === 0 && (
                      <div className="rounded border border-dashed border-slate-700 p-8 text-center text-sm text-slate-500">
                        All pending corrective actions have been approved and dispatched to field drivers.
                      </div>
                    )}
                  </div>
                </Panel>
              </div>
            )}

            {/* 5. ROUTE PLANNING VIEW */}
            {activeView === "Route Planning" && (
              <div className="mt-5 space-y-5">
                <Panel className="p-6">
                  <div className="border-b border-slate-800 pb-4">
                    <p className="text-sm font-semibold text-white">What-If Route Comparison for {selectedShipment.id}</p>
                    <p className="mt-1 text-xs text-slate-400">Compare 3 predictive routing options evaluated by the XGBoost & thermal decay model.</p>
                  </div>

                  <div className="mt-6 grid gap-4 lg:grid-cols-3">
                    {[
                      {
                        name: "Option A: Continue Current Route",
                        desc: "Proceed along Bangalore-Chennai NH44 without intervention.",
                        risk: "72%",
                        eta: "38 min",
                        safeLife: "38 min",
                        loss: "₹0 (₹1,85,000 at risk)",
                        recommended: false,
                      },
                      {
                        name: "Option B: Reroute to Cold Storage A (Guindy)",
                        desc: "Divert to verified warehouse cold room 12km away.",
                        risk: "14%",
                        eta: "22 min",
                        safeLife: "240 min",
                        loss: "₹1,85,000 saved",
                        recommended: true,
                      },
                      {
                        name: "Option C: Emergency Priority Delivery",
                        desc: "Fast-track delivery with auxiliary cooling boost.",
                        risk: "28%",
                        eta: "30 min",
                        safeLife: "45 min",
                        loss: "₹95,000 saved",
                        recommended: false,
                      }
                    ].map((plan) => (
                      <div key={plan.name} className={`rounded border p-5 ${plan.recommended ? "border-[#318368] bg-[#14261f]" : "border-slate-800 bg-[#0d161e]"}`}>
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-sm font-bold text-white">{plan.name}</p>
                          {plan.recommended && <span className="rounded bg-[#238767] px-2 py-0.5 text-[9px] font-bold uppercase text-white">AI Preferred</span>}
                        </div>
                        <p className="mt-2 text-xs leading-5 text-slate-400">{plan.desc}</p>

                        <div className="mt-5 grid grid-cols-2 gap-3 border-t border-slate-800 pt-4 text-xs">
                          <div><span className="text-slate-500">Projected Risk:</span><p className="mt-1 font-semibold text-white">{plan.risk}</p></div>
                          <div><span className="text-slate-500">Transit Time:</span><p className="mt-1 font-semibold text-white">{plan.eta}</p></div>
                          <div><span className="text-slate-500">Preserved Safe Life:</span><p className="mt-1 font-semibold text-white">{plan.safeLife}</p></div>
                          <div><span className="text-slate-500">Loss Avoided:</span><p className="mt-1 font-semibold text-[#74c8a7]">{plan.loss}</p></div>
                        </div>

                        <button
                          type="button"
                          onClick={() => approveAction(selectedShipment.id)}
                          className={`mt-5 w-full rounded py-2 text-xs font-semibold ${plan.recommended ? "bg-[#238767] text-white hover:bg-[#2c9c78]" : "border border-slate-700 text-slate-300 hover:bg-slate-800"}`}
                        >
                          {plan.recommended ? "Select Preferred Route" : "Select Alternative"}
                        </button>
                      </div>
                    ))}
                  </div>
                </Panel>
              </div>
            )}

            {/* 6. PRODUCT PROFILES VIEW */}
            {activeView === "Product Profiles" && (
              <div className="mt-5 space-y-5">
                <Panel className="p-6">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                    <div>
                      <p className="text-sm font-semibold text-white">Monitored Product Temperature Profiles</p>
                      <p className="mt-1 text-xs text-slate-400">Configured temperature envelopes, critical limits, and shelf life.</p>
                    </div>
                  </div>

                  <div className="mt-6 overflow-x-auto">
                    <table className="w-full min-w-[650px] text-left text-xs">
                      <thead className="border-b border-slate-800 text-[10px] font-bold uppercase tracking-[0.08em] text-slate-500">
                        <tr>
                          <th className="pb-3">Product Name</th>
                          <th className="pb-3">Category</th>
                          <th className="pb-3">Safe Range</th>
                          <th className="pb-3">Critical Max</th>
                          <th className="pb-3">Sensitivity</th>
                          <th className="pb-3">Max Shelf Life</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60">
                        {(productsList.length > 0 ? productsList : [
                          { name: "Fresh Milk", category: "Dairy", safeTempMin: 2, safeTempMax: 6, criticalTempMax: 8, temperatureSensitivity: "High", shelfLifeHours: 48 },
                          { name: "COVID-19 Vaccines", category: "Biologics", safeTempMin: 2, safeTempMax: 8, criticalTempMax: 10, temperatureSensitivity: "Critical", shelfLifeHours: 720 },
                          { name: "Insulin Glargine", category: "Pharmaceuticals", safeTempMin: 2, safeTempMax: 8, criticalTempMax: 12, temperatureSensitivity: "High", shelfLifeHours: 672 },
                          { name: "Fresh Seafood", category: "Perishables", safeTempMin: -2, safeTempMax: 2, criticalTempMax: 4, temperatureSensitivity: "High", shelfLifeHours: 36 },
                        ]).map((p) => (
                          <tr key={p.name} className="text-slate-300">
                            <td className="py-3.5 font-semibold text-white">{p.name}</td>
                            <td className="py-3.5 text-slate-400">{p.category}</td>
                            <td className="py-3.5 text-[#74c8a7] font-mono">{p.safeTempMin}°C – {p.safeTempMax}°C</td>
                            <td className="py-3.5 text-[#dfbd70] font-mono">{p.criticalTempMax}°C</td>
                            <td className="py-3.5">
                              <span className="rounded border border-amber-800/40 bg-amber-950/30 px-2 py-0.5 text-[10px] font-semibold text-amber-300">
                                {p.temperatureSensitivity}
                              </span>
                            </td>
                            <td className="py-3.5 text-slate-400">{p.shelfLifeHours} Hours</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Panel>
              </div>
            )}

            {/* 7. AUDIT REPORTS VIEW */}
            {activeView === "Audit Reports" && (
              <div className="mt-5 space-y-5">
                <Panel className="p-6">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800 pb-4">
                    <div>
                      <p className="text-sm font-semibold text-white">Chronological Compliance Audit Trail ({selectedShipment.id})</p>
                      <p className="mt-1 text-xs text-slate-400">Cryptographically verifiable event log from dispatch to verified handoff.</p>
                    </div>
                    <button type="button" onClick={() => setReportGenerated(true)} className="flex items-center gap-2 rounded bg-[#238767] px-4 py-2 text-xs font-semibold text-white hover:bg-[#2c9c78]">
                      <FileDown className="h-4 w-4" /> Export Signed Compliance Report
                    </button>
                  </div>

                  {reportGenerated && (
                    <div className="mt-4 rounded border border-[#2e7660] bg-[#14261f] p-4 text-xs text-[#83cfaf]">
                      ✓ Official Cold Chain Compliance Audit PDF compiled. Hash: <code className="font-mono">sha256-8a3f...d49b</code> ready for QA export.
                    </div>
                  )}

                  <div className="mt-6 border-l border-slate-700 pl-6 space-y-6">
                    {(auditTrail.length > 0 ? auditTrail : [
                      { timestamp: "08:06 AM", title: "Shipment Dispatched", stage: "DISPATCH", details: "Departure recorded at Bengaluru Hub with initial probe temperature of 4.1°C." },
                      { timestamp: "10:41 AM", title: "Thermal Excursion Detected", stage: "EXCURSION", details: "Probe T1 exceeded upper threshold (8.2°C). Causal delta ΔT/Δt triggered Fast Event Detector." },
                      { timestamp: "10:47 AM", title: "XGBoost V2 Risk Score Updated", stage: "PREDICTION", details: "Model inferred spoilage risk of 72% with TreeSHAP identifying spatial_range_t as primary driver." },
                      { timestamp: "10:49 AM", title: "Automated What-If Generated", stage: "RECOMMENDATION", details: "Calculated 3 routing alternatives. Recommended Reroute to Cold Storage A (Guindy) to avoid ₹1,85,000 loss." },
                      { timestamp: "10:52 AM", title: "Operator Confirmation", stage: "APPROVAL", details: "Operations admin approved reroute. Turn-by-turn navigation dispatched to field driver." }
                    ]).map((event, index) => (
                      <div key={index} className="relative">
                        <span className={`absolute -left-[31px] top-1 h-3 w-3 rounded-full border-2 border-[#101820] ${index === 0 ? "bg-[#278a69]" : index === 1 ? "bg-rose-500" : index === 2 ? "bg-amber-400" : "bg-[#278a69]"}`} />
                        <p className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#74c8a7]">{event.timestamp}</p>
                        <p className="mt-1 text-sm font-semibold text-white">{event.title}</p>
                        <p className="mt-1 text-xs leading-5 text-slate-400">{event.details}</p>
                      </div>
                    ))}
                  </div>
                </Panel>
              </div>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
