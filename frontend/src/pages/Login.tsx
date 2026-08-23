/**
 * Signal Chamber design system: a compact, high-contrast workspace login with real email/password authentication.
 */
import { Button } from "@/components/ui/button";
import { ArrowRight, KeyRound, Loader2, Radio } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { Link, useLocation } from "wouter";
import { api } from "../lib/api";

type LoginRole = "admin" | "field" | "client";

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

  const performLogin = async (loginEmail: string, loginPass: string, targetRole: LoginRole) => {
    setSubmitting(true);
    setIsError(false);
    setMessage("Authenticating…");
    try {
      const result = await api.login(loginEmail, loginPass);
      setMessage(`Welcome back, ${result.full_name}!`);
      window.setTimeout(() => {
        setLocation(targetRole === "field" ? "/field-agent" : targetRole === "client" ? "/client" : "/dashboard/admin");
      }, 400);
    } catch (err: any) {
      setIsError(true);
      setMessage(err.message || "Authentication failed. Please check your credentials.");
      setSubmitting(false);
    }
  };

  const login = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await performLogin(email, password, role);
  };

  const handleQuickDemo = (demoEmail: string, demoPass: string, demoRole: LoginRole) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setRole(demoRole);
    performLogin(demoEmail, demoPass, demoRole);
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

        <div className="mt-6 border-t border-white/10 pt-5">
          <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">⚡ Instant Demo Access</p>
          <div className="mt-3 grid grid-cols-3 gap-2">
            <button
              type="button"
              disabled={submitting}
              onClick={() => handleQuickDemo("admin@coldchain.ai", "admin123", "admin")}
              className="rounded border border-[#1D9E75]/40 bg-[#1D9E75]/10 py-2 text-center text-xs font-bold text-[#66d9b4] hover:bg-[#1D9E75]/20 disabled:opacity-50"
            >
              Fleet Admin
            </button>
            <button
              type="button"
              disabled={submitting}
              onClick={() => handleQuickDemo("driver@coldchain.ai", "driver123", "field")}
              className="rounded border border-[#1D9E75]/40 bg-[#1D9E75]/10 py-2 text-center text-xs font-bold text-[#66d9b4] hover:bg-[#1D9E75]/20 disabled:opacity-50"
            >
              Field Driver
            </button>
            <button
              type="button"
              disabled={submitting}
              onClick={() => handleQuickDemo("client@coldchain.ai", "client123", "client")}
              className="rounded border border-[#1D9E75]/40 bg-[#1D9E75]/10 py-2 text-center text-xs font-bold text-[#66d9b4] hover:bg-[#1D9E75]/20 disabled:opacity-50"
            >
              Client View
            </button>
          </div>
        </div>

        {message && <p className={`mt-4 flex items-center gap-2 text-xs ${isError ? "text-red-400" : "text-[#66d9b4]"}`}><Radio className="h-3.5 w-3.5" /> {message}</p>}
        <p className="mt-6 text-center text-sm text-slate-500">New to Cold Chain AI? <Link href="/signup" className="font-bold text-[#66d9b4] hover:text-white">Create your workspace</Link></p>
      </div>
    </main>
  );
}
