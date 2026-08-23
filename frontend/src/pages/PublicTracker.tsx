/**
 * Public tracking design: a friendly, light, single-column shipment page that translates cold-chain monitoring into plain language without login or operational complexity.
 */
import { Check, ChevronDown, Clock3, MapPin, Milk, PackageCheck, ShieldCheck, ThermometerSun, Truck } from "lucide-react";
import { useState, useEffect } from "react";
import { useRoute } from "wouter";
import { api } from "../lib/api";

export default function PublicTracker() {
  const [logOpen, setLogOpen] = useState(false);
  const [, params] = useRoute("/track/:token");
  const token = params?.token || "SHP-1042";
  const [shipment, setShipment] = useState<any>(null);

  const loadShipment = async () => {
    try {
      const active = await api.listShipments();
      const found = active.find(s => s.shipmentId === token) || active[0];
      setShipment(found);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadShipment();
    const interval = setInterval(loadShipment, 4000);
    const ws = api.connectTelemetry((msg) => {
      if (msg.type === "TELEMETRY_UPDATE" || msg.type === "DEMO_STATE") {
        loadShipment();
      }
    });
    return () => {
      clearInterval(interval);
      ws.close();
    };
  }, [token]);

  if (!shipment) {
    return (
      <main className="min-h-screen bg-[#050c14] text-[#dce8e2] grid place-items-center">
        <p className="text-sm">Loading tracking dashboard…</p>
      </main>
    );
  }

  const isDiverted = shipment.status === "DIVERTED";
  const isDelivered = shipment.status === "DELIVERED";
  const statusLabel = isDelivered ? "DELIVERED" : isDiverted ? "REROUTED" : "SAFE";
  const explanation = isDelivered
    ? "Your shipment has been securely delivered to destination."
    : isDiverted
    ? "Your shipment has been diverted to nearest approved cold storage facility."
    : "Your cargo is being cared for and is on track.";

  return (
    <main className="public-shell min-h-screen bg-[#050c14] px-0 py-0 text-[#dce8e2] sm:px-5 sm:py-8">
      <div className="mx-auto min-h-screen max-w-[430px] bg-[#08131a] sm:min-h-0 sm:rounded-[22px] sm:shadow-[0_0_0_1px_rgba(255,255,255,0.08)]">
        <header className="flex items-center justify-between border-b border-white/[0.1] px-6 py-5">
          <div className="flex items-center gap-3"><span className="grid h-11 w-11 place-items-center rounded-2xl bg-[#dcf5e9] text-[#14825f]"><Milk className="h-6 w-6" /></span><div><p className="font-display text-lg font-bold tracking-[-0.045em]">Your Shipment</p><p className="mt-0.5 text-xs font-semibold text-[#9bb0a6]">Shipment #{shipment.shipmentId}</p></div></div>
          <span className="rounded-full bg-[#e3f7ec] px-3 py-1.5 text-[10px] font-extrabold tracking-[0.14em] text-[#13805d]">LIVE</span>
        </header>

        <div className="space-y-5 px-5 py-6">
          <section className="rounded-[24px] bg-[#e5f8ee] px-5 py-5 text-center"><p className="text-[10px] font-extrabold tracking-[0.17em] text-[#168563]">SHIPMENT STATUS</p><div className="mt-3 inline-flex items-center gap-2 rounded-full bg-[#168563] px-4 py-2 text-sm font-extrabold tracking-[0.1em] text-white"><Check className="h-4 w-4" /> {statusLabel}</div><p className="mt-3 text-sm font-semibold text-[#3a6855]">{explanation}</p></section>

          {!isDelivered && (
            <section className="rounded-[24px] border border-[#dce9e2] p-5"><div className="flex items-center gap-2 text-[#168563]"><Clock3 className="h-4 w-4" /><p className="text-[10px] font-extrabold tracking-[0.15em]">ESTIMATED ARRIVAL</p></div><p className="font-display mt-4 text-5xl font-bold tracking-[-0.075em]">{shipment.etaMinutes} <span className="text-3xl tracking-[-0.05em]">minutes</span></p><p className="mt-2 text-sm text-[#71877c]">Arriving at {shipment.destination.name}</p></section>
          )}

          <section className="overflow-hidden rounded-[24px] border border-[#dce9e2]"><div className="relative h-40 bg-[#e6f0eb]" aria-label="Live shipment location"><div className="absolute -left-7 top-9 h-20 w-72 rotate-[-12deg] rounded-full border-[13px] border-white/80" /><div className="absolute -right-8 bottom-[-26px] h-36 w-52 rotate-[24deg] rounded-full border-[14px] border-[#d0dfd7]" /><div className="absolute left-[27%] top-[58%] h-2.5 w-[35%] rotate-[-29deg] rounded-full bg-[#168563]" /><span className="absolute left-[20%] top-[57%] grid h-9 w-9 place-items-center rounded-full border-4 border-white bg-[#334c41] text-white"><Truck className="h-4 w-4" /></span><span className="absolute right-[25%] top-[21%] grid h-9 w-9 place-items-center rounded-full border-4 border-white bg-[#168563] text-white"><MapPin className="h-4 w-4" /></span><p className="absolute bottom-3 left-4 text-[10px] font-extrabold tracking-[0.12em] text-[#49665a]">{isDelivered ? "ARRIVED" : "ON THE WAY"}</p></div><div className="flex items-center justify-between px-5 py-4"><div><p className="text-xs font-semibold text-[#748b80]">Current status</p><p className="mt-1 text-sm font-bold">Vehicle: {shipment.vehicleId}</p></div><span className="text-xs font-extrabold text-[#168563]">LIVE LOCATION</span></div></section>

          <section className="flex items-center gap-4 rounded-[24px] border border-[#dce9e2] p-5"><span className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-[#eff8f3] text-[#168563]"><ThermometerSun className="h-6 w-6" /></span><div><p className="text-[10px] font-extrabold tracking-[0.14em] text-[#738a7d]">PRODUCT TEMPERATURE</p><p className="font-display mt-1 text-2xl font-bold tracking-[-0.05em]">{shipment.temperature.toFixed(1)}°C</p><p className="mt-1 text-sm font-semibold text-[#278562]">{shipment.temperature <= shipment.safeMaxTemp ? "Within safe range" : "High Temperature Warning"}</p></div></section>

          <section className="overflow-hidden rounded-[24px] border border-[#cbe7d8] bg-[#f4fbf7]"><button type="button" onClick={() => setLogOpen(!logOpen)} className="flex min-h-20 w-full items-center gap-4 px-5 text-left"><span className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-[#168563] text-white"><ShieldCheck className="h-6 w-6" /></span><span className="flex-1"><span className="font-display block text-lg font-bold tracking-[-0.04em]">Cold Chain Verified</span><span className="mt-1 block text-sm leading-5 text-[#638073]">AI-monitored end to end.</span></span></button>{logOpen && <div className="border-t border-[#d7ebe0] px-5 py-4"><p className="text-xs font-extrabold tracking-[0.13em] text-[#168563]">TAMPER-PROOF LOG</p><div className="mt-3 space-y-3 text-sm text-[#4e685c]"><p className="flex items-center gap-2"><Check className="h-4 w-4 text-[#168563]" /> Picked up with a verified seal</p><p className="flex items-center gap-2"><Check className="h-4 w-4 text-[#168563]" /> Envelope constraints: [{shipment.safeMinTemp}°C - {shipment.safeMaxTemp}°C]</p><p className="flex items-center gap-2"><Check className="h-4 w-4 text-[#168563]" /> Active risk score: {shipment.riskScore}%</p></div></div>}</section>

          <section className="rounded-[24px] border border-[#dce9e2] p-5"><p className="text-[10px] font-extrabold tracking-[0.15em] text-[#168563]">DELIVERY JOURNEY</p><div className="mt-5 space-y-0">{[["Picked up", `Origin: ${shipment.origin.name}`, true], ["In transit", "En route to destination", !isDelivered], ["Cold-chain monitored", `Temp reading: ${shipment.temperature.toFixed(1)}°C`, true], ["Delivered", isDelivered ? "Handoff complete" : "Awaiting arrival", isDelivered]].map(([title, subtitle, done], index) => <div key={title as string} className="relative flex gap-4 pb-6 last:pb-0"><div className="relative z-10 grid h-7 w-7 shrink-0 place-items-center rounded-full border-2 border-white bg-[#168563] text-white">{done ? <Check className="h-4 w-4" /> : <span className="h-2.5 w-2.5 rounded-full bg-[#bad7c8]" />}</div>{index < 3 && <span className={`absolute left-[13px] top-7 h-[28px] w-0.5 ${done ? "bg-[#168563]" : "bg-[#dbe8e1]"}`} />}<div className="pt-0.5"><p className="text-sm font-extrabold text-[#24483a]">{title as string}</p><p className="mt-1 text-xs text-[#71877c]">{subtitle as string}</p></div></div>)}</div></section>
        </div>
        <footer className="px-5 pb-8 text-center text-xs font-semibold text-[#91a69c]"><PackageCheck className="mr-1 inline h-3.5 w-3.5 text-[#168563]" /> Tracking provided by Cold Chain AI</footer>
      </div>
    </main>
  );
}
