/**
 * Signal Chamber design system: a role-specific dashboard landing view using sparse layers, teal signals, and readable operational hierarchy.
 */
import { ArrowLeft, ArrowUpRight, BellRing, Building2, CircleAlert, CloudSnow, Eye, MapPin, Route, ShieldCheck, Truck, UserRound } from "lucide-react";
import { Link, useRoute } from "wouter";
import FieldAgent from "./FieldAgent";
import FieldWorkspace from "./FieldWorkspace";
import PublicTracker from "./PublicTracker";
import ClientWorkspace from "./ClientWorkspace";

const configurations = {
  admin: { title: "Admin / Ops", eyebrow: "NETWORK COMMAND", line: "Three exceptions are waiting for a decision.", icon: Building2, action: "Open exception queue", stat: "03", context: "active priority events" },
  field: { title: "Field Agent", eyebrow: "FIELD RESPONSE", line: "One response task is ready at the next handoff.", icon: Truck, action: "Open field task", stat: "01", context: "task awaiting confirmation" },
  client: { title: "Client / Viewer", eyebrow: "SHIPMENT VIEW", line: "Your cold-chain condition is being monitored in real time.", icon: UserRound, action: "View shipment status", stat: "98.7%", context: "condition confidence" },
} as const;

export default function RoleDashboard() {
  const [, params] = useRoute("/dashboard/:role");
  if (params?.role === "field") return <FieldWorkspace />;
  if (params?.role === "client") return <ClientWorkspace />;
  const roleKey = params?.role === "field" || params?.role === "client" ? params.role : "admin";
  const config = configurations[roleKey];
  const Icon = config.icon;

  return (
    <main className="min-h-screen bg-[#050c14] text-white">
      <header className="flex h-[72px] items-center justify-between border-b border-white/[0.1] bg-[#07101a] px-5 sm:px-8">
        <Link href="/" className="flex items-center gap-3"><img src="/manus-storage/cold-chain-mark_8a9c38e3.png" alt="Cold Chain AI" className="h-9 w-9" /><span className="font-display text-sm font-bold tracking-[-0.04em]">COLD CHAIN AI</span></Link>
        <Link href="/" className="inline-flex items-center gap-2 text-xs font-bold text-slate-400 transition-colors hover:text-[#66d9b4]"><ArrowLeft className="h-4 w-4" /> EXIT WORKSPACE</Link>
      </header>
      <div className="grid min-h-[calc(100vh-72px)] lg:grid-cols-[260px_1fr]">
        <aside className="hidden border-r border-white/[0.1] bg-[#07101a] p-6 lg:block">
          <p className="section-kicker">{config.eyebrow}</p>
          <div className="mt-8 flex items-center gap-3 border-l-2 border-[#1D9E75] bg-white/[0.04] px-4 py-3 text-sm font-bold"><Icon className="h-4 w-4 text-[#66d9b4]" /> Overview</div>
          <div className="mt-3 flex items-center gap-3 px-4 py-3 text-sm text-slate-500"><Route className="h-4 w-4" /> Active routes</div>
          <div className="mt-3 flex items-center gap-3 px-4 py-3 text-sm text-slate-500"><BellRing className="h-4 w-4" /> Notifications</div>
        </aside>
        <section className="relative overflow-hidden p-5 sm:p-8 lg:p-10">
          <div className="absolute inset-0 hero-grid-lines opacity-30" />
          <div className="relative mx-auto max-w-[1180px]">
            <div className="flex flex-col justify-between gap-6 sm:flex-row sm:items-end">
              <div><p className="section-kicker">WELCOME BACK</p><h1 className="font-display mt-4 text-5xl font-bold tracking-[-0.065em]">{config.title}</h1><p className="mt-3 text-slate-400">{config.line}</p></div>
              <button className="inline-flex h-11 items-center justify-center gap-2 border border-[#1D9E75]/50 bg-[#1D9E75]/10 px-5 text-sm font-bold text-[#66d9b4] transition-colors hover:bg-[#1D9E75]/20">{config.action} <ArrowUpRight className="h-4 w-4" /></button>
            </div>
            <div className="mt-10 grid gap-4 lg:grid-cols-[1.45fr_0.75fr]">
              <article className="border border-white/[0.1] bg-[#0a1721] p-6 sm:p-8">
                <div className="flex items-center justify-between"><div><p className="section-kicker">PRIORITY CONDITION</p><p className="font-display mt-4 text-3xl font-semibold tracking-[-0.055em]">Bengaluru → Pune</p></div><span className="grid h-12 w-12 place-items-center rounded-full border border-[#1D9E75]/30 bg-[#1D9E75]/10 text-[#66d9b4]"><CloudSnow className="h-5 w-5" /></span></div>
                <div className="mt-12 flex items-end gap-2" aria-label="Temperature telemetry chart">
                  {[42, 44, 38, 48, 53, 60, 58, 70, 74, 65, 57, 61, 54, 49, 42].map((height, index) => <span key={index} className={`block flex-1 ${index === 8 ? "bg-[#1D9E75]" : "bg-[#1D9E75]/35"}`} style={{ height: `${height}px` }} />)}
                </div>
                <div className="mt-5 flex items-center justify-between border-t border-white/[0.08] pt-5 text-xs"><span className="flex items-center gap-2 text-slate-400"><MapPin className="h-3.5 w-3.5 text-[#66d9b4]" /> 14 sensors responding</span><span className="font-bold text-[#66d9b4]">NO EXCURSION DETECTED</span></div>
              </article>
              <article className="border border-white/[0.1] bg-[#0a1721] p-6 sm:p-8"><p className="section-kicker">LIVE SIGNAL</p><div className="font-display mt-7 text-6xl font-semibold tracking-[-0.08em] text-white">{config.stat}</div><p className="mt-2 text-sm text-slate-400">{config.context}</p><div className="mt-10 border-t border-white/[0.08] pt-5"><div className="flex items-center gap-3 text-sm font-bold text-slate-200"><CircleAlert className="h-4 w-4 text-[#66d9b4]" /> AI response loop armed</div><p className="mt-2 text-xs leading-5 text-slate-500">Conditions are continuously assessed against your role’s decision protocol.</p></div></article>
            </div>
            <div className="mt-4 grid gap-4 md:grid-cols-3">
              {[['Telemetry', 'Normal', Eye], ['Decision trail', 'Current', ShieldCheck], ['Next scan', '07 min', BellRing]].map(([label, value, ItemIcon]) => { const Item = ItemIcon as typeof Eye; return <div key={label as string} className="flex items-center gap-4 border border-white/[0.09] bg-[#09151f] p-5"><span className="grid h-9 w-9 place-items-center rounded-full bg-[#1D9E75]/10 text-[#66d9b4]"><Item className="h-4 w-4" /></span><div><p className="text-xs text-slate-500">{label as string}</p><p className="mt-1 text-sm font-bold text-white">{value as string}</p></div></div>})}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
