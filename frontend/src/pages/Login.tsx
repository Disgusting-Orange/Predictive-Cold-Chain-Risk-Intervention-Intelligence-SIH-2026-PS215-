/**
 * Signal Chamber design system: a compact, high-contrast workspace login with real email/password authentication.
 */
import { Button } from "@/components/ui/button";
import { ArrowRight, KeyRound, Loader2, Radio } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { Link, useLocation } from "wouter";
import { api } from "../lib/api";

type LoginRole = "admin" | "field" | "client";

const demoCredentials: Record<LoginRole, { label: string; email: string; password: string }> = {
  admin: { label: "Admin / Ops", email: "admin@coldchain.ai", password: "admin123" },
  field: { label: "Field Agent", email: "driver@coldchain.ai", password: "driver123" },
  client: { label: "Client View", email: "client@coldchain.ai", password: "client123" },
};

export default function Login() {
  const [, setLocation] = useLocation();
  const [message, setMessage] = useState("");
  const [isError, setIsError] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [role, setRole] = useState<LoginRole>("admin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const requestedRole = new URLSearchParams(window.location.search).get("role");

  useEffect(() => {
    if (requestedRole === "admin" || requestedRole === "field" || requestedRole === "client") {
      setRole(requestedRole);
    }
  }, [requestedRole]);

  const roleDetails: Record<LoginRole, { eyebrow: string; title: string; description: string }> = {
    admin: { eyebrow: "ADMIN / OPS ACCESS", title: "Return to operations control.", description: "Review fleet health, exceptions, approvals, and shipment records." },
    field: { eyebrow: "FIELD AGENT ACCESS", title: "Open your field workspace.", description: "Receive assignments, navigate to approved storage, and confirm handoffs." },
    client: { eyebrow: "CLIENT ACCESS", title: "Open your shipment view.", description: "See delivery progress, condition, and protected shipment records." },
  };
  const currentRoleDetails = roleDetails[role];

  const useDemoCredentials = (demoRole: LoginRole) => {
    const demo = demoCredentials[demoRole];
    setRole(demoRole);
    setEmail(demo.email);
    setPassword(demo.password);
    setMessage(`${demo.label} demo credentials loaded.`);
    setIsError(false);
  };

  const login = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setIsError(false);
    setMessage("Authenticating…");
    try {
      const result = await api.login(email, password);
      setMessage(`Welcome back, ${result.full_name}!`);
      window.setTimeout(() => {
        setLocation(role === "field" ? "/field-agent" : role === "client" ? "/client" : "/dashboard/admin");
      }, 500);
    } catch (err: any) {
      setIsError(true);
      setMessage(err.message || "Authentication failed. Please check your credentials.");
      setSubmitting(false);
    }
  };

  return (
    <main className="relative grid min-h-screen place-items-center overflow-hidden bg-[#050c14] px-5 py-10 text-white">
      <div className="absolute inset-0 hero-grid-lines opacity-40" />
      <div className="absolute left-1/2 top-1/2 h-[470px] w-[470px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#1D9E75]/10 blur-[120px]" />
      <div className="relative w-full max-w-[470px] border border-white/[0.12] bg-[#09151f]/95 p-7 shadow-[0_24px_80px_rgba(0,0,0,0.35)] sm:p-9">
        <Link href="/" className="flex items-center gap-3"><img src="/manus-storage/cold-chain-mark_8a9c38e3.png" alt="Cold Chain AI" className="h-9 w-9" /><span className="font-display text-sm font-bold tracking-[-0.04em]">COLD CHAIN AI</span></Link>
        <div className="mt-9 flex items-center justify-between"><p className="section-kicker">{currentRoleDetails.eyebrow}</p><span className="grid h-9 w-9 place-items-center rounded-full border border-[#1D9E75]/40 bg-[#1D9E75]/10 text-[#66d9b4]"><KeyRound className="h-4 w-4" /></span></div>
        <h1 className="font-display mt-5 text-4xl font-bold tracking-[-0.065em]">{currentRoleDetails.title}</h1>
        <p className="mt-3 text-sm leading-6 text-slate-400">{currentRoleDetails.description}</p>
        <form onSubmit={login} className="mt-8 space-y-5">
          <label className="form-label">Work email<input required type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@company.com" className="signal-input mt-2" /></label>
          <label className="form-label">Password<input required type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Your password" className="signal-input mt-2" /></label>
          <label className="form-label">Open workspace as<select value={role} onChange={(event) => setRole(event.target.value as LoginRole)} className="signal-input mt-2"><option value="admin">Admin / Ops</option><option value="field">Field Agent</option><option value="client">Client View</option></select></label>
          <Button type="submit" disabled={submitting} className="h-13 w-full rounded-none bg-[#1D9E75] font-extrabold hover:bg-[#27ad84] disabled:opacity-60">
            {submitting ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Authenticating…</> : <>Sign in <ArrowRight className="ml-2 h-4 w-4" /></>}
          </Button>
        </form>
        <div className="mt-6 border border-dashed border-white/[0.14] p-3">
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">Demo access</p>
          <div className="mt-2 grid gap-2 sm:grid-cols-3">
            {(Object.keys(demoCredentials) as LoginRole[]).map((demoRole) => (
              <button key={demoRole} type="button" onClick={() => useDemoCredentials(demoRole)} className="border border-white/[0.12] px-2 py-2 text-left text-[11px] text-slate-300 transition hover:border-[#66d9b4] hover:text-white">
                <span className="block font-bold">{demoCredentials[demoRole].label}</span>
                <span className="mt-1 block truncate text-[10px] text-slate-500">{demoCredentials[demoRole].email}</span>
                <span className="block text-[10px] text-slate-500">{demoCredentials[demoRole].password}</span>
              </button>
            ))}
          </div>
        </div>
        {message && <p className={`mt-4 flex items-center gap-2 text-xs ${isError ? "text-red-400" : "text-[#66d9b4]"}`}><Radio className="h-3.5 w-3.5" /> {message}</p>}
        <p className="mt-8 text-center text-sm text-slate-500">New to Cold Chain AI? <Link href="/signup" className="font-bold text-[#66d9b4] hover:text-white">Create your workspace</Link></p>
      </div>
    </main>
  );
}
