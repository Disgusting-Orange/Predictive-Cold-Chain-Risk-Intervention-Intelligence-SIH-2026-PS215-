/**
 * Signal Chamber design system: a focused dark onboarding flow with teal decision states and spatial telemetry details.
 */
import { Button } from "@/components/ui/button";
import { ArrowLeft, ArrowRight, Building2, Check, CircleDot, Eye, Radio, Truck, UserRound } from "lucide-react";
import { FormEvent, useState } from "react";
import { Link, useLocation } from "wouter";
import { api } from "../lib/api";

const roleOptions = [
  { id: "admin", title: "Admin / Ops", description: "Set the playbook, manage exceptions, and coordinate your complete operating network.", icon: Building2, signal: "CONTROL ROOM" },
  { id: "field", title: "Field Agent", description: "Receive exact response tasks, confirm the corrective action, and keep handoffs moving.", icon: Truck, signal: "HANDOFF TEAM" },
  { id: "client", title: "Client / Viewer", description: "Follow your shipment’s condition and status with a clear, trusted view of progress.", icon: UserRound, signal: "SHIPMENT VIEW" },
];

export default function Signup() {
  const [, setLocation] = useLocation();
  const [stage, setStage] = useState<"signup" | "role">("signup");
  const [trackingCode, setTrackingCode] = useState("");
  const [trackingMessage, setTrackingMessage] = useState("");
  const [fullName, setFullName] = useState("");
  const [organization, setOrganization] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const submitSignup = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setStage("role");
  };

  const handleRoleSelect = async (roleId: string) => {
    try {
      const mappedRole = roleId === "field" ? "FIELD_AGENT" : roleId === "client" ? "CLIENT" : "ADMIN";
      await api.register({
        email,
        password,
        full_name: fullName,
        role: mappedRole,
        phone: ""
      });
      setLocation(roleId === "field" ? "/field-agent" : roleId === "client" ? "/client" : "/dashboard/admin");
    } catch (err: any) {
      alert("Registration failed: " + err.message);
    }
  };

  const openTracking = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!trackingCode.trim()) {
      setTrackingMessage("Enter your tracking link or shipment reference to continue.");
      return;
    }
    setLocation(`/track/${encodeURIComponent(trackingCode.trim())}`);
  };

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#050c14] px-5 py-6 text-white sm:px-8 lg:px-10">
      <div className="absolute inset-0 hero-grid-lines opacity-45" />
      <div className="absolute -right-28 top-20 h-[480px] w-[480px] rounded-full bg-[#1D9E75]/10 blur-[120px]" />
      <div className="absolute left-[12%] top-[17%] h-3 w-3 rounded-full bg-[#1D9E75] shadow-[0_0_30px_8px_rgba(29,158,117,0.45)]" />
      <div className="relative mx-auto max-w-[1320px]">
        <header className="flex flex-col items-start gap-4 sm:flex-row sm:items-center sm:justify-between">
          <Link href="/" className="flex items-center gap-3" aria-label="Back to Cold Chain AI home">
            <img src="/manus-storage/cold-chain-mark_8a9c38e3.png" alt="Cold Chain AI" className="h-10 w-10" />
            <div className="leading-none"><div className="font-display text-[15px] font-bold tracking-[-0.04em]">COLD CHAIN</div><div className="mt-1 text-[9px] font-bold tracking-[0.28em] text-[#66d9b4]">AI / CONTROL</div></div>
          </Link>
          <div className="text-sm text-slate-400">Already have a workspace? <Link href="/login" className="font-bold text-[#66d9b4] hover:text-white">Log in</Link></div>
        </header>

        <div className="grid min-h-[calc(100vh-100px)] items-center gap-14 py-14 lg:grid-cols-[0.9fr_1.1fr] lg:py-20">
          <div className="hidden max-w-lg lg:block">
            <p className="section-kicker">YOUR OPERATING LAYER</p>
            <h1 className="font-display mt-6 text-6xl font-bold leading-[0.92] tracking-[-0.07em]">Build a better<br /><span className="text-[#66d9b4]">response path.</span></h1>
            <p className="mt-8 max-w-md leading-7 text-slate-400">Cold Chain AI adapts your view to the work you own—network response, field action, or shipment visibility.</p>
            <div className="mt-12 border-l border-[#1D9E75]/50 pl-5">
              <p className="font-display text-2xl font-semibold tracking-[-0.05em]">Predict → Suggest → Act</p>
              <p className="mt-2 text-sm leading-6 text-slate-500">One shared decision trail from early signal to confirmed correction.</p>
            </div>
          </div>

          <section className="relative ml-auto w-full max-w-[620px] border border-white/[0.12] bg-[#09151f]/95 p-6 shadow-[0_24px_80px_rgba(0,0,0,0.28)] sm:p-9">
            <div className="absolute right-0 top-0 h-16 w-16 border-l border-b border-[#1D9E75]/50" />
            {stage === "signup" ? (
              <>
                <div className="flex items-center justify-between">
                  <p className="section-kicker">01 / ACCOUNT SETUP</p>
                  <span className="grid h-9 w-9 place-items-center rounded-full border border-[#1D9E75]/40 bg-[#1D9E75]/10 text-[#66d9b4]"><Radio className="h-4 w-4" /></span>
                </div>
                <h2 className="font-display mt-6 text-4xl font-bold tracking-[-0.06em]">Set up your workspace.</h2>
                <p className="mt-3 max-w-md text-sm leading-6 text-slate-400">Start with the operational basics. You will choose the right view on the next step.</p>
                <form onSubmit={submitSignup} className="mt-8 grid gap-5 sm:grid-cols-2">
                  <label className="form-label">Full name<input required value={fullName} onChange={e => setFullName(e.target.value)} name="name" placeholder="Your name" className="signal-input mt-2" /></label>
                  <label className="form-label">Organization<input required value={organization} onChange={e => setOrganization(e.target.value)} name="organization" placeholder="Company name" className="signal-input mt-2" /></label>
                  <label className="form-label sm:col-span-2">Work email<input required type="email" value={email} onChange={e => setEmail(e.target.value)} name="email" placeholder="you@company.com" className="signal-input mt-2" /></label>
                  <label className="form-label sm:col-span-2">Password<input required minLength={8} type="password" value={password} onChange={e => setPassword(e.target.value)} name="password" placeholder="At least 8 characters" className="signal-input mt-2" /></label>
                  <Button type="submit" className="mt-2 h-13 rounded-none bg-[#1D9E75] text-[15px] font-extrabold hover:bg-[#27ad84] sm:col-span-2">Continue to role selection <ArrowRight className="ml-2 h-4 w-4" /></Button>
                </form>
                <div className="mt-8 border-t border-white/[0.1] pt-6">
                  <p className="text-sm font-semibold text-slate-200">Tracking a shipment? <span className="text-slate-500">Use your tracking link instead.</span></p>
                  <form onSubmit={openTracking} className="mt-4 flex flex-col gap-3 sm:flex-row">
                    <input value={trackingCode} onChange={(event) => setTrackingCode(event.target.value)} className="signal-input h-11 flex-1" placeholder="Paste tracking link or shipment ID" />
                    <Button type="submit" variant="outline" className="h-11 rounded-none border-white/20 bg-transparent px-5 text-white hover:border-[#1D9E75] hover:bg-[#1D9E75]/10 hover:text-white">Open tracking <Eye className="ml-2 h-4 w-4" /></Button>
                  </form>
                  {trackingMessage && <p className="mt-3 flex items-center gap-2 text-xs text-[#66d9b4]"><Check className="h-3.5 w-3.5" /> {trackingMessage}</p>}
                </div>
              </>
            ) : (
              <>
                <div className="flex items-center justify-between">
                  <button type="button" onClick={() => setStage("signup")} className="inline-flex items-center gap-2 text-xs font-bold tracking-[0.1em] text-slate-400 transition-colors hover:text-white"><ArrowLeft className="h-4 w-4" /> BACK</button>
                  <span className="section-kicker">02 / ROLE SELECTION</span>
                </div>
                <h2 className="font-display mt-6 text-4xl font-bold tracking-[-0.06em]">Choose your command view.</h2>
                <p className="mt-3 max-w-md text-sm leading-6 text-slate-400">Your role calibrates the first dashboard. You can adjust workspace access later.</p>
                <div className="mt-8 grid gap-3">
                  {roleOptions.map((role) => {
                    const Icon = role.icon;
                    return (
                      <button key={role.id} type="button" onClick={() => handleRoleSelect(role.id)} className="group grid grid-cols-[auto_1fr_auto] items-center gap-4 border border-white/[0.1] bg-[#0b1a24] p-5 text-left transition-all duration-200 hover:-translate-y-0.5 hover:border-[#1D9E75]/70 hover:bg-[#10242d]">
                        <span className="grid h-11 w-11 place-items-center rounded-full border border-[#1D9E75]/35 bg-[#1D9E75]/10 text-[#66d9b4]"><Icon className="h-5 w-5" /></span>
                        <span><span className="font-display block text-xl font-bold tracking-[-0.045em] text-white">{role.title}</span><span className="mt-1 block max-w-[330px] text-sm leading-5 text-slate-400">{role.description}</span><span className="mt-3 block text-[9px] font-bold tracking-[0.16em] text-[#66d9b4]">{role.signal}</span></span>
                        <ArrowRight className="h-5 w-5 text-slate-600 transition-all group-hover:translate-x-1 group-hover:text-[#66d9b4]" />
                      </button>
                    );
                  })}
                </div>
              </>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}
