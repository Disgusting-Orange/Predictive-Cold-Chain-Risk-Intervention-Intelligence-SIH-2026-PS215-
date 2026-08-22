/**
 * Field Agent mobile design: a single-shipment, delivery-rideshare-style workflow with oversized touch controls, sparse status, and immediate next actions.
 */
import {
  ArrowLeft,
  ArrowUpRight,
  Camera,
  Check,
  ChevronRight,
  CircleAlert,
  CloudSnow,
  MapPin,
  Navigation,
  PackageCheck,
  Route,
  ShieldCheck,
  ThermometerSun,
  X,
} from "lucide-react";
import { useState } from "react";
import { Link } from "wouter";

const tabs = ["My Shipment", "Current Risk", "AI Recommendation", "Navigation", "Handoff"];

export default function FieldAgent() {
  const [accepted, setAccepted] = useState(false);
  const [backupCooling, setBackupCooling] = useState(false);
  const [photoAdded, setPhotoAdded] = useState(false);
  const [handoffConfirmed, setHandoffConfirmed] = useState(false);
  const [activeTab, setActiveTab] = useState("My Shipment");
  const [rejected, setRejected] = useState(false);

  return (
    <main className="field-shell min-h-screen bg-[#050c14] text-[#dce8e2]">
      <div className="mx-auto min-h-screen max-w-[420px] bg-[#08131a] pb-24">
        <header className="field-header sticky top-0 z-30 flex items-center justify-between border-b border-white/[0.1] bg-[#08131a]/95 px-5 py-4 backdrop-blur">
          <div className="flex items-center gap-3">
            <Link href="/" className="grid h-10 w-10 place-items-center rounded-full border border-[#c9ddd3] bg-white text-[#168563]" aria-label="Back to Cold Chain AI home"><ArrowLeft className="h-5 w-5" /></Link>
            <div><p className="text-[11px] font-extrabold uppercase tracking-[0.16em] text-[#6b8177]">Current shipment</p><h1 className="font-display text-xl font-bold tracking-[-0.04em]">Shipment #CC-1024</h1></div>
          </div>
          <span className="grid h-10 w-10 place-items-center rounded-full bg-[#daf5e9] text-[#168563]"><CloudSnow className="h-5 w-5" /></span>
        </header>

        <section className="px-5 pt-5">
          <div className="flex items-center justify-between"><div><p className="text-sm font-bold text-[#30483e]">Milk <span className="font-medium text-[#789086]">| Batch M102</span></p><p className="mt-1 text-xs text-[#71877c]">Bengaluru Hub → Pune Retail</p></div><span className="rounded-full bg-[#dff2e9] px-3 py-1.5 text-[10px] font-extrabold tracking-[0.12em] text-[#17805f]">IN TRANSIT</span></div>
        </section>

        {!accepted ? (
          <div className="px-5 pb-6 pt-5">
            <section className="field-risk relative overflow-hidden rounded-[22px] border border-[#d95858]/35 bg-[#0d1d24] px-6 py-6 text-white">
              <div className="flex items-start justify-between"><div><p className="text-xs font-extrabold tracking-[0.16em]">CURRENT RISK</p><p className="risk-title mt-3 font-display text-4xl font-bold tracking-[-0.06em]">HIGH RISK</p></div><CircleAlert className="h-7 w-7 text-[#ff9a96]" /></div>
              <div className="mt-8 flex items-end justify-between border-t border-white/25 pt-5"><div><p className="text-xs font-semibold text-white/75">Spoilage risk</p><p className="font-display mt-1 text-5xl font-bold tracking-[-0.075em]">72%</p></div><div className="text-right"><p className="text-xs font-semibold text-white/75">Safe life remaining</p><p className="font-display mt-1 text-3xl font-bold tracking-[-0.055em]">38 min</p></div></div>
            </section>

            <section className="mt-5 rounded-[24px] border border-[#cfe2d8] bg-white p-5 shadow-[0_8px_22px_rgba(17,53,41,0.06)]">
              <div className="flex items-center justify-between"><div className="flex items-center gap-2 text-[#168563]"><span className="grid h-8 w-8 place-items-center rounded-full bg-[#dff5ea]"><Route className="h-4 w-4" /></span><p className="text-xs font-extrabold tracking-[0.13em]">AI RECOMMENDATION</p></div><span className="text-[10px] font-bold text-[#748a80]">NOW</span></div>
              <h2 className="font-display mt-5 text-3xl font-bold leading-[0.95] tracking-[-0.055em]">Move to<br />Cold Storage A</h2>
              <div className="mt-5 grid grid-cols-2 gap-3"><div className="rounded-2xl bg-[#eff6f2] p-3"><p className="text-[10px] font-extrabold uppercase tracking-[0.12em] text-[#748a80]">Distance</p><p className="font-display mt-1 text-xl font-bold">3.2 km</p></div><div className="rounded-2xl bg-[#eff6f2] p-3"><p className="text-[10px] font-extrabold uppercase tracking-[0.12em] text-[#748a80]">ETA</p><p className="font-display mt-1 text-xl font-bold">8 min</p></div></div>
              <p className="mt-4 text-sm leading-6 text-[#567066]">The closest monitored facility can protect the remaining safe life.</p>
              <button type="button" onClick={() => { setAccepted(true); setActiveTab("Navigation"); }} className="mt-6 flex min-h-14 w-full items-center justify-center gap-2 rounded-2xl bg-[#168563] px-5 text-base font-extrabold text-white transition hover:bg-[#116e51] active:scale-[0.98]">Accept &amp; Reroute <Navigation className="h-5 w-5" /></button>
              <button type="button" onClick={() => setRejected(true)} className="mt-3 flex min-h-14 w-full items-center justify-center gap-2 rounded-2xl border border-[#b8cec2] bg-white px-5 text-base font-extrabold text-[#325044] transition hover:border-[#768f83] active:scale-[0.98]">Reject <X className="h-5 w-5" /></button>
              {rejected && <p className="mt-4 rounded-xl bg-[#fff4df] px-4 py-3 text-sm font-semibold text-[#8d5a14]">Recommendation rejected. Continue monitoring this shipment closely.</p>}
            </section>
          </div>
        ) : (
          <div className="px-5 pb-6 pt-5">
            <section className="rounded-[24px] bg-[#168563] p-5 text-white"><div className="flex items-center gap-3"><span className="grid h-10 w-10 place-items-center rounded-full bg-white/15"><Check className="h-5 w-5" /></span><div><p className="text-[10px] font-extrabold tracking-[0.15em] text-[#c6f1df]">REROUTE ACCEPTED</p><p className="font-display mt-1 text-xl font-bold tracking-[-0.04em]">Cold Storage A is ready.</p></div></div></section>

            <section className="mt-5 overflow-hidden rounded-[24px] border border-[#cfe2d8] bg-white p-5">
              <div className="flex items-center justify-between"><div><p className="text-[10px] font-extrabold tracking-[0.14em] text-[#168563]">LIVE NAVIGATION</p><h2 className="font-display mt-2 text-2xl font-bold tracking-[-0.05em]">Head to Cold Storage A</h2></div><span className="grid h-10 w-10 place-items-center rounded-full bg-[#daf5e9] text-[#168563]"><Navigation className="h-5 w-5" /></span></div>
              <div className="relative mt-6 h-40 overflow-hidden rounded-2xl bg-[#e5efe9]" aria-label="Route map from current location to Cold Storage A">
                <div className="absolute -left-5 top-[-48px] h-36 w-52 rotate-[24deg] rounded-full border-[14px] border-white/70" /><div className="absolute -right-7 bottom-[-50px] h-44 w-64 rotate-[-18deg] rounded-full border-[15px] border-[#d0dfd7]" />
                <div className="absolute left-[24%] top-[57%] h-2.5 w-[50%] rotate-[-14deg] rounded-full bg-[#168563]" />
                <span className="absolute left-[19%] top-[49%] grid h-8 w-8 place-items-center rounded-full border-4 border-white bg-[#263f34] text-white"><MapPin className="h-3.5 w-3.5" /></span><span className="absolute right-[18%] top-[25%] grid h-9 w-9 place-items-center rounded-full border-4 border-white bg-[#168563] text-white"><PackageCheck className="h-4 w-4" /></span>
                <p className="absolute bottom-3 left-4 text-[10px] font-extrabold tracking-[0.12em] text-[#466257]">CURRENT LOCATION</p><p className="absolute right-3 top-3 text-[10px] font-extrabold tracking-[0.12em] text-[#168563]">COLD STORAGE A</p>
              </div>
              <div className="mt-5 flex items-center justify-between"><div><p className="text-xs text-[#70887d]">Distance</p><p className="font-display mt-1 text-2xl font-bold tracking-[-0.05em]">3.2 km</p></div><div className="h-10 w-px bg-[#dbe7e1]" /><div className="text-right"><p className="text-xs text-[#70887d]">Arrival in</p><p className="font-display mt-1 text-2xl font-bold tracking-[-0.05em]">8 min</p></div></div>
            </section>

            <section className="mt-5 grid grid-cols-2 gap-3"><div className="rounded-[22px] border border-[#cfe2d8] bg-white p-4"><div className="flex items-center gap-2 text-[#168563]"><ThermometerSun className="h-4 w-4" /><p className="text-[10px] font-extrabold tracking-[0.12em]">TEMPERATURE</p></div><p className="font-display mt-3 text-3xl font-bold tracking-[-0.06em]">8.2°C <span className="text-[#b63535]">↑</span></p><p className="mt-1 text-xs text-[#71877c]">Trending upward</p></div><div className="rounded-[22px] border border-[#cfe2d8] bg-white p-4"><div className="flex items-center gap-2 text-[#168563]"><ShieldCheck className="h-4 w-4" /><p className="text-[10px] font-extrabold tracking-[0.12em]">SAFE LIFE</p></div><p className="font-display mt-3 text-3xl font-bold tracking-[-0.06em]">30 min</p><p className="mt-1 text-xs text-[#71877c]">After reroute</p></div></section>

            <section className="mt-5 rounded-[24px] border border-[#cfe2d8] bg-white p-5"><div className="flex gap-3"><span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-[#dff5ea] text-[#168563]"><CloudSnow className="h-5 w-5" /></span><div><p className="font-display text-xl font-bold tracking-[-0.045em]">Backup Cooling Available</p><p className="mt-1 text-sm leading-5 text-[#637a6f]">Use backup cooling while en route to reduce temperature rise.</p></div></div><button type="button" onClick={() => setBackupCooling(!backupCooling)} className={`mt-5 flex min-h-14 w-full items-center justify-center gap-2 rounded-2xl px-4 text-base font-extrabold transition active:scale-[0.98] ${backupCooling ? "bg-[#daf5e9] text-[#168563]" : "bg-[#168563] text-white hover:bg-[#116e51]"}`}>{backupCooling ? <><Check className="h-5 w-5" /> Backup cooling active</> : <>Activate Backup Cooling <CloudSnow className="h-5 w-5" /></>}</button></section>

            <section className="mt-5 rounded-[24px] border border-[#cfe2d8] bg-white p-5"><p className="text-[10px] font-extrabold tracking-[0.14em] text-[#168563]">FINAL HANDOFF</p><h2 className="font-display mt-2 text-2xl font-bold tracking-[-0.05em]">Proof for the next handoff.</h2><p className="mt-2 text-sm leading-6 text-[#637a6f]">Capture the product at Cold Storage A, then close out the reroute.</p><button type="button" onClick={() => setPhotoAdded(true)} className={`mt-5 flex min-h-14 w-full items-center justify-center gap-2 rounded-2xl border px-4 text-base font-extrabold transition active:scale-[0.98] ${photoAdded ? "border-[#8fd5bb] bg-[#daf5e9] text-[#168563]" : "border-dashed border-[#98b9a9] bg-[#f5faf7] text-[#315346]"}`}><Camera className="h-5 w-5" /> {photoAdded ? "Handoff photo added" : "Upload Handoff Photo"}</button><button type="button" onClick={() => setHandoffConfirmed(true)} disabled={!photoAdded} className="mt-3 flex min-h-14 w-full items-center justify-center gap-2 rounded-2xl bg-[#168563] px-4 text-base font-extrabold text-white transition hover:bg-[#116e51] disabled:cursor-not-allowed disabled:bg-[#b7c9c0]">Confirm Handoff <ChevronRight className="h-5 w-5" /></button>{handoffConfirmed && <p className="mt-4 flex items-center gap-2 rounded-xl bg-[#daf5e9] px-4 py-3 text-sm font-bold text-[#168563]"><Check className="h-4 w-4" /> Handoff confirmed. Shipment #CC-1024 is protected.</p>}</section>
          </div>
        )}

        <nav className="fixed bottom-0 left-1/2 z-40 flex w-full max-w-[420px] -translate-x-1/2 border-t border-[#d8e5de] bg-white px-2 py-2" aria-label="Field Agent navigation">
          {tabs.map((tab) => <button key={tab} type="button" onClick={() => setActiveTab(tab)} className={`flex min-h-12 flex-1 flex-col items-center justify-center gap-1 rounded-xl px-1 text-[9px] font-bold leading-none transition ${activeTab === tab ? "bg-[#daf5e9] text-[#168563]" : "text-[#758b80]"}`}><span className={`h-1.5 w-1.5 rounded-full ${activeTab === tab ? "bg-[#168563]" : "bg-transparent"}`} />{tab.replace("AI Recommendation", "AI Rec.")}</button>)}
        </nav>
      </div>
    </main>
  );
}
