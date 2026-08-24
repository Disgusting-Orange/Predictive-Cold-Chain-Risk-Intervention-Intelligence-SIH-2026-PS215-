/**
 * Signal Chamber design system: an asymmetric dark-navy landing page where teal telemetry and layered isometric forms visualize predictive cold-chain control.
 */
import { Button } from "@/components/ui/button";
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  BadgeCheck,
  BrainCircuit,
  Building2,
  Check,
  ChevronDown,
  CircleDot,
  CloudSnow,
  Command,
  Menu,
  Radio,
  ScanLine,
  ShieldCheck,
  Sparkles,
  Truck,
  UserRound,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "wouter";

const navItems = [
  { label: "Why Cold Chain AI", target: "#how-it-works" },
  { label: "Solutions", target: "#solutions" },
  { label: "Industries", target: "#industries" },
  { label: "About", target: "#about" },
];

const steps = [
  {
    number: "01",
    title: "Predict",
    short: "Risk signals, before the excursion.",
    text: "Cold Chain AI connects telemetry, lane behavior, and live ambient conditions to surface risk while there is still time to respond.",
    icon: BrainCircuit,
    image: "/manus-storage/cold-chain-sensor-halo_4f0b4184.png",
    metric: "6.2 h",
    metricLabel: "average early warning",
  },
  {
    number: "02",
    title: "Suggest",
    short: "A next best action, not another alert.",
    text: "Every anomaly is scored against your SOPs, cargo sensitivity, and operational context—so teams see the most practical intervention first.",
    icon: Sparkles,
    metric: "3 paths",
    metricLabel: "ranked for each event",
  },
  {
    number: "03",
    title: "Act",
    short: "Close the loop across every handoff.",
    text: "Route decisions to the right person, keep a decision trail, and confirm that a temperature risk became a protected shipment.",
    icon: Command,
    image: "/manus-storage/cold-chain-response-path_876d3fca.png",
    metric: "1 loop",
    metricLabel: "from signal to proof",
  },
];

const roles = [
  {
    title: "Admin / Ops",
    description: "Configure SOPs, coordinate exceptions, and operate from the network view.",
    icon: Building2,
    code: "OPS-01",
  },
  {
    title: "Field Agent",
    description: "Receive a precise task, verify action at the handoff, and close the loop in minutes.",
    icon: Truck,
    code: "FIELD-02",
  },
  {
    title: "Client / Viewer",
    description: "Track the shipment, understand the condition, and stay informed without operational overhead.",
    icon: UserRound,
    code: "VIEW-03",
  },
];

function SignalMark({ size = "normal" }: { size?: "normal" | "small" }) {
  return (
    <img
      src="/manus-storage/cold-chain-mark_8a9c38e3.png"
      alt="Cold Chain AI"
      className={size === "small" ? "h-8 w-8" : "h-10 w-10"}
    />
  );
}

export default function Home() {
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const elements = document.querySelectorAll<HTMLElement>(".reveal");
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12 },
    );
    elements.forEach((element) => observer.observe(element));
    return () => observer.disconnect();
  }, []);

  return (
    <main className="min-h-screen overflow-hidden bg-[#050c14] text-white selection:bg-[#1D9E75] selection:text-white">
      <header className="fixed inset-x-0 top-0 z-50 border-b border-white/[0.07] bg-[#07101a]/80 backdrop-blur-xl">
        <div className="mx-auto flex h-[76px] max-w-[1440px] items-center justify-between px-5 lg:px-10">
          <Link href="/" className="flex items-center gap-3" aria-label="Cold Chain AI home">
            <SignalMark />
            <div className="leading-none">
              <div className="font-display text-[15px] font-bold tracking-[-0.04em] text-white">COLD CHAIN</div>
              <div className="mt-1 text-[9px] font-bold tracking-[0.32em] text-[#66d9b4]">AI / CONTROL</div>
            </div>
          </Link>

          <nav className="hidden items-center gap-7 lg:flex" aria-label="Primary navigation">
            {navItems.map((item) => (
              <a key={item.label} href={item.target} className="text-sm font-medium text-slate-300 transition-colors hover:text-white">
                {item.label}
              </a>
            ))}
          </nav>

          <div className="hidden items-center gap-2 min-[1180px]:flex">
            <Link href="/login?role=admin" className="rounded border border-white/10 px-3 py-2 text-xs font-bold text-slate-300 transition-colors hover:border-[#1D9E75]/60 hover:text-[#66d9b4]">Admin / Ops</Link>
            <Link href="/login?role=field" className="rounded border border-white/10 px-3 py-2 text-xs font-bold text-slate-300 transition-colors hover:border-[#1D9E75]/60 hover:text-[#66d9b4]">Field Agent</Link>
            <Link href="/login?role=client" className="rounded border border-white/10 px-3 py-2 text-xs font-bold text-slate-300 transition-colors hover:border-[#1D9E75]/60 hover:text-[#66d9b4]">Client View</Link>
            <Button asChild className="h-11 rounded-none bg-[#1D9E75] px-5 font-bold text-white shadow-[0_0_28px_rgba(29,158,117,0.18)] hover:bg-[#26ae84]">
              <Link href="/signup">Schedule a Demo <ArrowUpRight className="ml-2 h-4 w-4" /></Link>
            </Button>
          </div>

          <button
            type="button"
            className="grid h-10 w-10 place-items-center border border-white/10 text-white lg:hidden"
            aria-label="Toggle menu"
            onClick={() => setMenuOpen(!menuOpen)}
          >
            {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
        {menuOpen && (
          <div className="border-t border-white/10 bg-[#07101a] px-5 py-5 lg:hidden">
            <div className="flex flex-col gap-4">
              {navItems.map((item) => (
                <a key={item.label} href={item.target} onClick={() => setMenuOpen(false)} className="text-sm font-semibold text-slate-200">
                  {item.label}
                </a>
              ))}
              <div className="grid grid-cols-3 gap-2"><Link href="/login?role=admin" className="rounded border border-white/10 px-2 py-2 text-center text-[11px] font-bold text-slate-300" onClick={() => setMenuOpen(false)}>Admin / Ops</Link><Link href="/login?role=field" className="rounded border border-white/10 px-2 py-2 text-center text-[11px] font-bold text-slate-300" onClick={() => setMenuOpen(false)}>Field</Link><Link href="/login?role=client" className="rounded border border-white/10 px-2 py-2 text-center text-[11px] font-bold text-slate-300" onClick={() => setMenuOpen(false)}>Client</Link></div>
              <Button asChild className="mt-1 rounded-none bg-[#1D9E75] font-bold hover:bg-[#26ae84]">
                <Link href="/signup" onClick={() => setMenuOpen(false)}>Schedule a Demo <ArrowUpRight className="ml-2 h-4 w-4" /></Link>
              </Button>
            </div>
          </div>
        )}
      </header>

      <section className="relative isolate min-h-[790px] overflow-hidden pt-[76px] lg:min-h-[850px]">
        <div className="absolute inset-0 hero-vignette" />
        <div className="absolute inset-0 opacity-70 hero-grid-lines" />
        <div className="absolute inset-y-0 right-0 w-full bg-[linear-gradient(90deg,#07101a_6%,rgba(7,16,26,0.92)_35%,rgba(7,16,26,0.3)_72%,#07101a_100%)]" />
        <img src="/manus-storage/cold-chain-hero-isometric_30d95e28.png" alt="Layered cold chain monitoring abstraction" className="absolute right-[-20%] top-[8%] h-[72%] w-[98%] object-cover object-right opacity-80 mix-blend-screen lg:right-[-3%] lg:top-[7%] lg:h-[89%] lg:w-[69%]" />
        <div className="hero-glow absolute right-[3%] top-[21%] h-[440px] w-[440px] rounded-full bg-[#1D9E75]/[0.13] blur-[125px]" />
        <div className="absolute bottom-0 left-0 right-0 h-52 bg-gradient-to-t from-[#050c14] via-[#050c14]/75 to-transparent" />

        <div className="absolute right-[6%] top-[31%] hidden h-64 w-64 lg:block" aria-hidden="true">
          <div className="hero-slab hero-slab-top" />
          <div className="hero-slab hero-slab-mid" />
          <div className="hero-slab hero-slab-bottom" />
          <div className="hero-orb hero-orb-a" />
          <div className="hero-orb hero-orb-b" />
          <div className="hero-orb hero-orb-c" />
        </div>

        <div className="relative mx-auto flex min-h-[714px] max-w-[1440px] items-center px-5 pb-20 pt-20 lg:min-h-[774px] lg:px-10 lg:pb-28 lg:pt-28">
          <div className="max-w-3xl">
            <div className="reveal flex items-center gap-3 text-[11px] font-extrabold tracking-[0.22em] text-[#6ee0bb]">
              <span className="h-px w-8 bg-[#1D9E75]" />
              PREDICTIVE COLD-CHAIN CONTROL
            </div>
            <h1 className="reveal reveal-delay-1 font-display mt-7 max-w-[810px] text-[clamp(3.35rem,7.2vw,7rem)] font-bold leading-[0.91] tracking-[-0.075em] text-white">
              Predict spoilage.<br />
              Prevent <span className="text-[#37c69a]">loss.</span>
            </h1>
            <p className="reveal reveal-delay-2 mt-8 max-w-xl text-base leading-8 text-slate-300 sm:text-lg">
              Closed-loop AI monitoring for Indian logistics—so every temperature signal becomes an early decision, not a late report.
            </p>
            <div className="reveal reveal-delay-3 mt-10 flex flex-wrap items-center gap-3">
              <Button asChild size="lg" className="h-13 rounded-none bg-[#1D9E75] px-6 text-[15px] font-extrabold shadow-[0_12px_35px_rgba(29,158,117,0.22)] hover:bg-[#27ad84]">
                <Link href="/dashboard/admin">Open Live Control Room <ArrowRight className="ml-2 h-4 w-4" /></Link>
              </Button>
              <Button asChild variant="outline" size="lg" className="h-13 rounded-none border-white/20 bg-white/[0.025] px-5 text-[14px] font-bold text-white hover:border-[#1D9E75] hover:bg-white/[0.08] hover:text-white">
                <Link href="/field-agent">Field Driver View <Truck className="ml-2 h-4 w-4 text-[#66d9b4]" /></Link>
              </Button>
              <Button asChild variant="outline" size="lg" className="h-13 rounded-none border-white/20 bg-white/[0.025] px-5 text-[14px] font-bold text-white hover:border-[#1D9E75] hover:bg-white/[0.08] hover:text-white">
                <Link href="/client">Client Pharmacy View <Activity className="ml-2 h-4 w-4 text-[#66d9b4]" /></Link>
              </Button>
            </div>
            <div className="reveal reveal-delay-4 mt-14 flex items-center gap-4 text-xs text-slate-400">
              <div className="flex -space-x-1.5">
                <span className="grid h-7 w-7 place-items-center rounded-full border-2 border-[#07101a] bg-[#183547]"><CloudSnow className="h-3.5 w-3.5 text-[#6ee0bb]" /></span>
                <span className="grid h-7 w-7 place-items-center rounded-full border-2 border-[#07101a] bg-[#1d3b35]"><Radio className="h-3.5 w-3.5 text-[#6ee0bb]" /></span>
                <span className="grid h-7 w-7 place-items-center rounded-full border-2 border-[#07101a] bg-[#1a3349]"><ShieldCheck className="h-3.5 w-3.5 text-[#6ee0bb]" /></span>
              </div>
              <span>From warehouse <span className="text-slate-200">to last-mile handoff</span></span>
            </div>
          </div>
        </div>

        <a href="#how-it-works" className="absolute bottom-8 left-5 z-10 hidden items-center gap-3 text-[10px] font-bold tracking-[0.22em] text-slate-400 transition-colors hover:text-[#6ee0bb] lg:left-10 lg:flex">
          <span className="grid h-9 w-9 place-items-center rounded-full border border-white/15"><ChevronDown className="h-4 w-4" /></span>
          FOLLOW THE SIGNAL
        </a>
        <div className="absolute bottom-9 right-5 z-10 hidden text-right lg:right-10 lg:block">
          <div className="font-display text-3xl font-semibold tracking-[-0.05em] text-white">01 <span className="text-[#1D9E75]">/</span> 03</div>
          <div className="mt-1 text-[10px] font-bold tracking-[0.2em] text-slate-500">LIVE RISK INTELLIGENCE</div>
        </div>
      </section>

      <section id="how-it-works" className="relative border-y border-white/[0.08] bg-[#09131d] py-24 lg:py-32">
        <div className="telemetry-line absolute left-[6%] top-0 hidden h-full w-px bg-gradient-to-b from-transparent via-[#1D9E75]/60 to-transparent lg:block" />
        <div className="mx-auto max-w-[1440px] px-5 lg:px-10">
          <div className="reveal grid gap-8 lg:grid-cols-[0.86fr_1.14fr] lg:items-end">
            <div>
              <p className="section-kicker">HOW IT WORKS</p>
              <h2 className="font-display mt-5 max-w-lg text-5xl font-bold leading-[0.96] tracking-[-0.065em] text-white sm:text-6xl">
                One signal.<br /><span className="text-[#66d9b4]">Three moves.</span>
              </h2>
            </div>
            <p className="max-w-xl text-base leading-8 text-slate-400 lg:mb-1 lg:justify-self-end">
              Monitoring tells you what happened. Cold Chain AI completes the operational loop before small deviations become spoiled inventory, SLA breaches, or difficult calls.
            </p>
          </div>

          <div className="mt-16 grid gap-5 lg:grid-cols-3">
            {steps.map((step, index) => {
              const Icon = step.icon;
              return (
                <article key={step.title} className={`reveal reveal-delay-${index + 1} group relative min-h-[465px] overflow-hidden border border-white/[0.1] bg-[#0c1823] p-6 transition-all duration-300 hover:-translate-y-1 hover:border-[#1D9E75]/60 hover:bg-[#0e1d28] sm:p-8`}>
                  {step.image ? (
                    <img src={step.image} alt="" aria-hidden="true" className="absolute inset-x-0 bottom-0 h-[52%] w-full object-cover opacity-[0.2] mix-blend-screen transition duration-500 group-hover:scale-105 group-hover:opacity-[0.3]" />
                  ) : (
                    <div className="absolute bottom-0 right-0 h-56 w-full overflow-hidden opacity-80" aria-hidden="true">
                      <div className="suggest-platform suggest-platform-one" />
                      <div className="suggest-platform suggest-platform-two" />
                      <div className="suggest-platform suggest-platform-three" />
                      <div className="suggest-route" />
                    </div>
                  )}
                  <div className="relative flex items-center justify-between">
                    <span className="font-display text-xl font-semibold tracking-[-0.05em] text-[#6ee0bb]">{step.number}</span>
                    <span className="grid h-11 w-11 place-items-center rounded-full border border-white/10 bg-white/[0.04] text-[#6ee0bb]"><Icon className="h-5 w-5" /></span>
                  </div>
                  <div className="relative mt-16">
                    <h3 className="font-display text-4xl font-bold tracking-[-0.06em] text-white">{step.title}</h3>
                    <p className="mt-3 max-w-[260px] font-semibold leading-6 text-slate-200">{step.short}</p>
                    <p className="mt-4 max-w-sm text-sm leading-6 text-slate-400">{step.text}</p>
                  </div>
                  <div className="relative mt-8 border-t border-white/[0.1] pt-5">
                    <div className="font-display text-2xl font-semibold tracking-[-0.05em] text-white">{step.metric}</div>
                    <div className="mt-1 text-[10px] font-bold tracking-[0.16em] text-slate-500">{step.metricLabel.toUpperCase()}</div>
                  </div>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      <section id="solutions" className="relative bg-[#07101a] py-20 lg:py-24">
        <div className="mx-auto max-w-[1440px] px-5 lg:px-10">
          <div className="reveal relative overflow-hidden border-y border-white/[0.11] bg-[#081822] px-6 py-10 sm:px-10 lg:px-12">
            <div className="absolute -right-24 top-1/2 h-56 w-56 -translate-y-1/2 rounded-full border border-[#1D9E75]/20" />
            <div className="absolute -right-6 top-1/2 h-40 w-40 -translate-y-1/2 rounded-full border border-[#1D9E75]/30" />
            <div className="relative grid gap-10 lg:grid-cols-[1.15fr_2fr] lg:items-center">
              <div>
                <p className="section-kicker">NETWORK PULSE</p>
                <h2 className="font-display mt-4 text-4xl font-bold tracking-[-0.06em] text-white">Keep risk visible.<br />Keep teams ahead.</h2>
              </div>
              <div className="grid gap-8 sm:grid-cols-3">
                {[
                  ["2.4M+", "shipments monitored", Radio],
                  ["17%", "spoilage prevented", ShieldCheck],
                  ["6.2 hr", "average prediction lead time", Activity],
                ].map(([value, label, Icon], index) => {
                  const StatIcon = Icon as typeof Radio;
                  return (
                    <div key={label as string} className={`border-l border-white/10 pl-5 reveal reveal-delay-${index + 1}`}>
                      <StatIcon className="h-4 w-4 text-[#6ee0bb]" />
                      <div className="font-display mt-5 text-4xl font-semibold tracking-[-0.065em] text-white">{value as string}</div>
                      <p className="mt-1 text-xs leading-5 text-slate-400">{label as string}</p>
                    </div>
                  );
                })}
              </div>
            </div>
            <p className="relative mt-8 text-[10px] font-medium tracking-wide text-slate-500">ILLUSTRATIVE NETWORK PERFORMANCE METRICS — RESULTS VARY BY LANE, CARGO, AND RESPONSE PROTOCOL.</p>
          </div>
        </div>
      </section>

      <section id="industries" className="relative overflow-hidden bg-[#09131d] py-24 lg:py-32">
        <div className="absolute inset-0 opacity-45 hero-grid-lines" />
        <div className="relative mx-auto max-w-[1440px] px-5 lg:px-10">
          <div className="reveal grid gap-12 lg:grid-cols-[0.75fr_1.25fr]">
            <div>
              <p className="section-kicker">ROLE-AWARE BY DESIGN</p>
              <h2 className="font-display mt-5 text-5xl font-bold leading-[0.95] tracking-[-0.065em] text-white sm:text-6xl">The right move reaches the <span className="text-[#66d9b4]">right role.</span></h2>
              <p className="mt-7 max-w-md leading-7 text-slate-400">Every user enters the same decision loop from a different point. Cold Chain AI keeps that experience focused, without losing the audit trail.</p>
              <Link href="/signup" className="mt-8 inline-flex items-center gap-2 text-sm font-bold text-[#66d9b4] transition-all hover:gap-3">Explore role access <ArrowRight className="h-4 w-4" /></Link>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              {roles.map((role, index) => {
                const Icon = role.icon;
                return (
                  <Link key={role.title} href="/signup" className={`reveal reveal-delay-${index + 1} group min-h-[270px] border border-white/[0.1] bg-[#0c1823]/80 p-6 transition-all duration-300 hover:-translate-y-1 hover:border-[#1D9E75]/70 hover:bg-[#10212b]`}>
                    <div className="flex items-center justify-between">
                      <span className="grid h-10 w-10 place-items-center rounded-full border border-[#1D9E75]/35 bg-[#1D9E75]/10 text-[#66d9b4]"><Icon className="h-5 w-5" /></span>
                      <span className="text-[9px] font-bold tracking-[0.15em] text-slate-600">{role.code}</span>
                    </div>
                    <h3 className="font-display mt-16 text-2xl font-bold tracking-[-0.05em] text-white">{role.title}</h3>
                    <p className="mt-3 text-sm leading-6 text-slate-400">{role.description}</p>
                    <span className="mt-5 inline-flex items-center gap-1 text-xs font-bold text-[#66d9b4] opacity-0 transition-opacity group-hover:opacity-100">Choose role <ArrowRight className="h-3.5 w-3.5" /></span>
                  </Link>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      <section className="relative overflow-hidden border-y border-white/[0.08] bg-[#06101a] py-24 lg:py-28">
        <div className="absolute left-[10%] top-[20%] h-px w-[80%] bg-gradient-to-r from-transparent via-[#1D9E75]/40 to-transparent" />
        <div className="relative mx-auto max-w-[970px] px-5 text-center">
          <div className="reveal mx-auto grid h-14 w-14 place-items-center rounded-full border border-[#1D9E75]/35 bg-[#1D9E75]/10 text-[#6ee0bb]"><ScanLine className="h-6 w-6" /></div>
          <p className="reveal reveal-delay-1 section-kicker mt-7">READY WHEN THE SIGNAL ARRIVES</p>
          <h2 className="reveal reveal-delay-2 font-display mt-5 text-5xl font-bold leading-[0.95] tracking-[-0.07em] text-white sm:text-6xl">Make the next<br /><span className="text-[#66d9b4]">hour count.</span></h2>
          <p className="reveal reveal-delay-3 mx-auto mt-7 max-w-xl leading-7 text-slate-400">Set up your operating role, connect your monitoring data, and give every exception a timely path forward.</p>
          <Button asChild size="lg" className="reveal reveal-delay-4 mt-10 h-13 rounded-none bg-[#1D9E75] px-7 text-[15px] font-extrabold shadow-[0_12px_35px_rgba(29,158,117,0.18)] hover:bg-[#27ad84]">
            <Link href="/signup">Start your workspace <ArrowRight className="ml-2 h-4 w-4" /></Link>
          </Button>
        </div>
      </section>

      <footer id="about" className="bg-[#050c14] px-5 py-10 lg:px-10">
        <div className="mx-auto flex max-w-[1440px] flex-col justify-between gap-8 border-b border-white/[0.1] pb-9 sm:flex-row sm:items-end">
          <div className="flex items-center gap-3">
            <SignalMark size="small" />
            <div>
              <div className="font-display text-sm font-bold tracking-[-0.04em] text-white">COLD CHAIN AI</div>
              <div className="mt-1 text-[9px] font-bold tracking-[0.2em] text-[#66d9b4]">PREDICT / SUGGEST / ACT</div>
            </div>
          </div>
          <div className="flex flex-wrap gap-x-6 gap-y-3 text-xs font-semibold text-slate-400">
            <a href="#how-it-works" className="hover:text-[#66d9b4]">Platform</a>
            <a href="#industries" className="hover:text-[#66d9b4]">Roles</a>
            <Link href="/signup" className="hover:text-[#66d9b4]">Get started</Link>
            <Link href="/login" className="hover:text-[#66d9b4]">Log in</Link>
          </div>
        </div>
        <div className="mx-auto flex max-w-[1440px] flex-col gap-3 pt-6 text-[10px] font-semibold tracking-[0.08em] text-slate-600 sm:flex-row sm:items-center sm:justify-between">
          <span>© 2026 COLD CHAIN AI. BUILT FOR THE MOMENT BEFORE LOSS.</span>
          <span>INDIA / CLOSED-LOOP LOGISTICS INTELLIGENCE</span>
        </div>
      </footer>
    </main>
  );
}
