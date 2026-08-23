/**
 * Client desktop design: a calm, clear shipment command view that keeps the customer informed through large delivery status, condition, and order-record surfaces.
 */
import { Bell, Check, ChevronDown, Clock3, FileText, LogOut, MapPin, PackageCheck, ShieldCheck, ThermometerSun, Truck } from "lucide-react";
import { useState, useEffect } from "react";
import { Link, useLocation } from "wouter";
import { api } from "../lib/api";

export default function ClientWorkspace() {
  const [, setLocation] = useLocation();
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const handleSignOut = () => { localStorage.removeItem("token"); setLocation("/login"); };
  const [logOpen, setLogOpen] = useState(false);
  const [shipments, setShipments] = useState<any[]>([]);
  const [activeShipmentId, setActiveShipmentId] = useState("");
  const [selectedShipment, setSelectedShipment] = useState<any>(null);

  const loadShipments = async () => {
    try {
      const active = await api.listShipments();
      setShipments(active);
      if (active.length > 0) {
        if (!activeShipmentId) {
          setActiveShipmentId(active[0].shipmentId);
          setSelectedShipment(active[0]);
        } else {
          const updated = active.find(s => s.shipmentId === activeShipmentId);
          if (updated) setSelectedShipment(updated);
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadShipments();
    const ws = api.connectTelemetry((msg) => {
      if (msg.type === "TELEMETRY_UPDATE" || msg.type === "DEMO_STATE") {
        loadShipments();
      }
    });
    return () => ws.close();
  }, [activeShipmentId]);

  const handleSelectShipment = (id: string) => {
    setActiveShipmentId(id);
    const found = shipments.find(s => s.shipmentId === id);
    if (found) setSelectedShipment(found);
  };

  if (!selectedShipment) {
    return (
      <main className="min-h-screen bg-[#edf3f0] text-[#142d24] grid place-items-center">
        <p className="text-sm text-slate-500">Loading deliveries…</p>
      </main>
    );
  }

  const isDiverted = selectedShipment.status === "DIVERTED";
  const isDelivered = selectedShipment.status === "DELIVERED";
  const statusLabel = isDelivered ? "Delivered" : isDiverted ? "Diverted (Safe)" : "On track";

  return (
    <main className="client-desktop min-h-screen bg-[#edf3f0] text-[#142d24]">
      <header className="sticky top-0 z-30 flex h-[68px] items-center justify-between border-b border-[#d5e1db] bg-white px-5 lg:px-10"><div className="flex items-center gap-3"><img src="/manus-storage/cold-chain-mark_8a9c38e3.png" alt="Cold Chain AI" className="h-9 w-9" /><div><p className="font-display text-[14px] font-bold uppercase tracking-[0.1em] text-[#163a2d]">Cold Chain <span className="text-[#168563]">AI</span></p><p className="text-[8px] font-bold uppercase tracking-[0.18em] text-[#799087]">Client portal</p></div></div><nav className="hidden items-center gap-7 text-sm font-semibold text-[#547066] md:flex"><span className="text-[#168563]">My shipments</span><span>Documents</span><span>Support</span></nav><div className="flex items-center gap-3"><button type="button" className="relative grid h-9 w-9 place-items-center rounded border border-[#d5e1db] text-[#476359]"><Bell className="h-4 w-4" /><span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-[#d56560]" /></button><div className="relative"><button type="button" onClick={() => setUserMenuOpen(!userMenuOpen)} className="flex items-center gap-2 rounded border border-[#d5e1db] bg-white px-2 py-1.5"><span className="grid h-7 w-7 place-items-center rounded bg-[#168563] text-[10px] font-bold text-white">NK</span><span className="hidden text-xs font-semibold text-[#28483b] sm:block">Nandita K.</span><ChevronDown className={`hidden h-3 w-3 text-[#7e9389] transition-transform sm:block ${userMenuOpen ? "rotate-180" : ""}`} /></button>{userMenuOpen && <div className="absolute right-0 top-full z-50 mt-1 w-48 border border-[#d5e1db] bg-white shadow-xl"><div className="border-b border-[#d5e1db] px-4 py-3"><p className="text-xs font-semibold text-[#163a2d]">Apollo Hospital Pharmacy</p><p className="mt-0.5 text-[10px] text-[#799087]">client@coldchain.ai</p></div><button type="button" onClick={handleSignOut} className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-sm text-[#547066] hover:bg-[#f1f6f3] hover:text-[#163a2d]"><LogOut className="h-3.5 w-3.5" /> Sign out</button></div>}</div></div></header>
      <div className="mx-auto max-w-[1480px] px-5 py-8 lg:px-10"><div className="flex flex-col justify-between gap-4 border-b border-[#d5e1db] pb-6 sm:flex-row sm:items-end"><div><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#168563]">CLIENT SHIPMENT VIEW</p><h1 className="font-display mt-3 text-4xl font-bold tracking-[-0.06em] text-[#153b2d]">Your deliveries</h1><p className="mt-2 text-sm text-[#60776c]">Clear updates on every active cold-chain shipment.</p></div><div className="flex items-center gap-3"><span className="text-sm font-semibold text-[#61796d]">Active shipment</span><select value={activeShipmentId} onChange={(event) => handleSelectShipment(event.target.value)} className="h-10 rounded border border-[#cddbd4] bg-white px-3 text-sm font-semibold text-[#28483b] outline-none">
        {shipments.map(s => <option key={s.shipmentId} value={s.shipmentId}>{s.shipmentId} · {s.productName}</option>)}
      </select></div></div>

        <section className="mt-6 grid gap-5 xl:grid-cols-[1.1fr_0.9fr]"><article className="relative overflow-hidden border border-[#d5e1db] bg-white p-7 before:absolute before:left-0 before:top-0 before:h-1 before:w-12 before:bg-[#168563]"><div className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#168563]">Shipment {selectedShipment.shipmentId}</p><h2 className="font-display mt-3 text-5xl font-bold tracking-[-0.07em] text-[#183d2f]">{isDelivered ? "Delivered at Destination" : <>Arriving in<br /><span className="text-[#168563]">{selectedShipment.etaMinutes} minutes</span></>}</h2><p className="mt-4 text-sm text-[#637b70]">{selectedShipment.productName} · Vehicle {selectedShipment.vehicleId} · Delivering to {selectedShipment.destination.name}</p></div><span className="inline-flex items-center gap-2 rounded border border-[#a8d8c1] bg-[#eff9f3] px-3 py-2 text-xs font-bold uppercase tracking-[0.1em] text-[#168563]"><Check className="h-4 w-4" /> {statusLabel}</span></div><div className="relative mt-8 h-[250px] overflow-hidden border border-[#d9e5df] bg-[#e7f0eb]"><div className="absolute left-[15%] top-[62%] h-1 w-[68%] -rotate-[27deg] bg-[#168563]/80" /><div className="absolute -left-5 top-3 h-48 w-[70%] rotate-[-17deg] rounded-full border-[24px] border-white/80" /><div className="absolute right-[-58px] bottom-[-54px] h-64 w-[45%] rotate-[20deg] rounded-full border-[24px] border-[#cddcd4]" /><span className="absolute left-[18%] top-[57%] grid h-10 w-10 place-items-center rounded-full border-4 border-white bg-[#28483b] text-white"><Truck className="h-4 w-4" /></span><span className="absolute right-[16%] top-[20%] grid h-10 w-10 place-items-center rounded-full border-4 border-white bg-[#168563] text-white"><MapPin className="h-4 w-4" /></span><span className="absolute bottom-4 left-4 text-[10px] font-bold uppercase tracking-[0.1em] text-[#537065]">Near {selectedShipment.destination.name}</span><span className="absolute right-4 top-4 text-[10px] font-bold uppercase tracking-[0.1em] text-[#168563]">{selectedShipment.destination.name}</span></div></article><article className="relative overflow-hidden border border-[#d5e1db] bg-white p-7 before:absolute before:left-0 before:top-0 before:h-1 before:w-12 before:bg-[#168563]"><div className="flex items-center justify-between"><div><p className="text-xs font-semibold text-[#2f5747]">Product condition</p><p className="mt-1 text-sm text-[#6b8378]">Telemetry updated dynamically</p></div><ThermometerSun className="h-5 w-5 text-[#168563]" /></div><div className="mt-8 flex items-end justify-between border-b border-[#dce7e1] pb-7"><div><p className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#7c9287]">Current temperature</p><p className="font-display mt-2 text-5xl font-bold tracking-[-0.08em] text-[#183d2f]">{selectedShipment.temperature.toFixed(1)}°C</p></div><div className="text-right"><p className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#7c9287]">Condition</p><p className="mt-2 text-sm font-bold text-[#168563]">{selectedShipment.temperature <= selectedShipment.safeMaxTemp ? "Within safe range" : "High Temperature Alert"}</p></div></div><button type="button" onClick={() => setLogOpen(!logOpen)} className="mt-7 flex w-full items-center justify-between border border-[#c7dfd2] bg-[#f2faf6] px-4 py-4 text-left"><span className="flex items-center gap-3"><span className="grid h-10 w-10 place-items-center rounded bg-[#168563] text-white"><ShieldCheck className="h-5 w-5" /></span><span><span className="block text-sm font-bold text-[#254d3d]">Cold Chain Verified</span><span className="mt-1 block text-xs text-[#6d8579]">AI-monitored end to end.</span></span></span><ChevronDown className={`h-4 w-4 text-[#168563] transition-transform ${logOpen ? "rotate-180" : ""}`} /></button>{logOpen && <div className="border-x border-b border-[#c7dfd2] bg-white px-4 py-4"><p className="text-[10px] font-bold uppercase tracking-[0.1em] text-[#168563]">Verification record</p><div className="mt-3 grid gap-2 text-sm text-[#547165]"><p className="flex gap-2"><Check className="h-4 w-4 text-[#168563]" /> Seal verified at pickup</p><p className="flex gap-2"><Check className="h-4 w-4 text-[#168563]" /> Temperature operating envelope [ {selectedShipment.safeMinTemp}°C - {selectedShipment.safeMaxTemp}°C ]</p><p className="flex gap-2"><Check className="h-4 w-4 text-[#168563]" /> Spoilage risk index: {selectedShipment.riskScore}%</p></div></div>}</article></section>

        <section className="mt-6 grid gap-5 xl:grid-cols-[1.05fr_0.95fr]"><article className="relative overflow-hidden border border-[#d5e1db] bg-white p-6 before:absolute before:left-0 before:top-0 before:h-1 before:w-12 before:bg-[#168563]"><p className="text-xs font-semibold text-[#2f5747]">Delivery journey</p><div className="mt-6 grid gap-3 md:grid-cols-4">{[["Picked up", selectedShipment.origin.name, true, PackageCheck], ["In transit", `Vehicle ${selectedShipment.vehicleId}`, !isDelivered, Truck], ["Monitored", `Temp: ${selectedShipment.temperature.toFixed(1)}°C`, true, ShieldCheck], ["Delivered", isDelivered ? "Handoff verified" : `Expected in ${selectedShipment.etaMinutes} min`, isDelivered, MapPin]].map(([title, note, done, ItemIcon], index) => { const Icon = ItemIcon as typeof PackageCheck; return <div key={title as string} className="relative border border-[#dce7e1] p-4"><span className={`grid h-8 w-8 place-items-center rounded-full ${done ? "bg-[#168563] text-white" : "bg-[#e7f0eb] text-[#8aa095]"}`}><Icon className="h-4 w-4" /></span>{index < 3 && <span className="absolute -right-3 top-8 hidden h-px w-6 bg-[#bcd8ca] md:block" />}<p className="mt-4 text-sm font-bold text-[#294c3e]">{title as string}</p><p className="mt-1 text-xs text-[#748b80]">{note as string}</p></div>; })}</div></article><article className="relative overflow-hidden border border-[#d5e1db] bg-white p-6 before:absolute before:left-0 before:top-0 before:h-1 before:w-12 before:bg-[#168563]"><div className="flex items-center justify-between"><div><p className="text-xs font-semibold text-[#2f5747]">Shipment documents</p><p className="mt-1 text-sm text-[#6b8378]">Records linked to this delivery.</p></div><FileText className="h-5 w-5 text-[#168563]" /></div><div className="mt-5 divide-y divide-[#dce7e1] border-y border-[#dce7e1]">{[["Delivery note", "Available"], ["Temperature summary", "Available"], ["Proof of handoff", isDelivered ? "Available" : "Pending"]].map(([name, status]) => <div key={name as string} className="flex items-center justify-between py-3"><span className="text-sm font-semibold text-[#2e5344]">{name as string}</span><span className={`text-xs font-bold ${status === "Available" ? "text-[#168563]" : "text-[#9a7b3d]"}`}>{status as string}</span></div>)}</div><Link href={`/track/${selectedShipment.shipmentId}`} className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-[#168563] hover:text-[#204f3f]">Open shareable tracking page <Clock3 className="h-4 w-4" /></Link></article></section>
      </div>
    </main>
  );
}
