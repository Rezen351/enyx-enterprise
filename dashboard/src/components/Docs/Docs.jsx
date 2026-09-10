import { BookOpen, ArrowLeft, AlertTriangle, Info, Lightbulb, ShieldCheck } from 'lucide-react';

/* ------------------------------------------------------------------ *
 *  Small presentational helpers (kept local to the docs page)
 * ------------------------------------------------------------------ */

function Callout({ type = 'info', title, children }) {
  const map = {
    info: { icon: Info, cls: 'border-emerald-500/30 bg-emerald-500/5 text-emerald-300' },
    note: { icon: Info, cls: 'border-emerald-500/30 bg-emerald-500/5 text-emerald-300' },
    tip: { icon: Lightbulb, cls: 'border-teal-500/30 bg-teal-500/5 text-teal-300' },
    warning: { icon: AlertTriangle, cls: 'border-amber-500/30 bg-amber-500/5 text-amber-300' },
  };
  const { icon: Icon, cls } = map[type] || map.info;
  return (
    <div className={`flex gap-3 border p-4 my-6 ${cls}`}>
      <Icon className="w-5 h-5 shrink-0 mt-0.5" />
      <div className="text-sm leading-relaxed">
        {title && <div className="font-black uppercase tracking-widest text-[11px] mb-1">{title}</div>}
        <div style={{ color: 'var(--text-muted)' }}>{children}</div>
      </div>
    </div>
  );
}

function CodeBlock({ code }) {
  return (
    <pre className="bg-[#040c08] border border-emerald-500/15 p-4 my-5 overflow-x-auto font-mono text-[12.5px] leading-relaxed text-emerald-200">
      <code>{code}</code>
    </pre>
  );
}

function H2({ id, children }) {
  return (
    <h2 id={id} className="scroll-mt-24 text-2xl sm:text-3xl font-black uppercase tracking-tight mt-16 mb-5 pb-3 border-b" style={{ color: 'var(--text-main)', borderColor: 'var(--border-main)' }}>
      {children}
    </h2>
  );
}

function H3({ children }) {
  return (
    <h3 className="text-lg font-black uppercase tracking-wider mt-8 mb-3" style={{ color: 'var(--text-main)' }}>
      {children}
    </h3>
  );
}

function P({ children }) {
  return <p className="text-sm sm:text-[15px] leading-relaxed mb-4" style={{ color: 'var(--text-muted)' }}>{children}</p>;
}

function Inline({ children }) {
  return <code className="font-mono text-[12.5px] px-1.5 py-0.5 bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">{children}</code>;
}

function Table({ head, rows }) {
  return (
    <div className="overflow-x-auto my-6 border" style={{ borderColor: 'var(--border-main)' }}>
      <table className="w-full text-left text-[13px] border-collapse">
        <thead>
          <tr style={{ backgroundColor: 'var(--bg-card)' }}>
            {head.map((h) => (
              <th key={h} className="px-4 py-3 font-black uppercase tracking-widest text-[11px]" style={{ color: 'var(--text-main)', borderBottom: '1px solid var(--border-main)' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="odd:bg-[#040c08]/40">
              {r.map((c, j) => (
                <td key={j} className="px-4 py-3 align-top" style={{ color: 'var(--text-muted)', borderBottom: '1px solid var(--border-main)' }}>{c}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ------------------------------------------------------------------ *
 *  Documentation content
 * ------------------------------------------------------------------ */

const SECTIONS = [
  { id: 'overview', label: 'Overview' },
  { id: 'architecture', label: 'Architecture' },
  { id: 'quickstart', label: 'Quickstart' },
  { id: 'concepts', label: 'Core Concepts' },
  { id: 'services', label: 'Services' },
  { id: 'dataflow', label: 'Telemetry & Data Flow' },
  { id: 'auth', label: 'Authentication' },
  { id: 'dashboard', label: 'Using the Dashboard' },
  { id: 'api', label: 'API Reference' },
  { id: 'security', label: 'Security' },
  { id: 'operations', label: 'Operations' },
];

export default function Docs({ onBack }) {
  const scrollTo = (id) => {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <div className="min-h-screen font-sans selection:bg-emerald-500/30 relative" style={{ backgroundColor: 'var(--bg-main)', color: 'var(--text-main)' }}>
      {/* Header */}
      <header className="sticky top-0 z-50 border-b backdrop-blur-xl" style={{ borderColor: 'var(--border-main)', backgroundColor: 'var(--bg-main)' }}>
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between compact-mobile-px">
          <div className="flex items-center gap-3">
            <BookOpen className="w-6 h-6 text-emerald-400" />
            <span className="text-sm font-black uppercase tracking-[0.2em]">Documentation</span>
          </div>
          <button onClick={onBack} className="flex items-center gap-2 text-emerald-500 hover:text-emerald-400 font-bold uppercase tracking-widest text-xs cursor-pointer">
            <ArrowLeft className="w-4 h-4" /> Back to Home
          </button>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-10 flex gap-12 compact-mobile-px">
        {/* Table of contents */}
        <aside className="hidden lg:block w-60 shrink-0">
          <nav className="sticky top-24 space-y-1">
            <div className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-500 mb-4">On this page</div>
            {SECTIONS.map((s) => (
              <button
                key={s.id}
                onClick={() => scrollTo(s.id)}
                className="block w-full text-left px-3 py-2 text-[13px] font-medium tracking-wide transition-colors hover:text-emerald-400 hover:bg-emerald-500/5 cursor-pointer"
                style={{ color: 'var(--text-muted)' }}
              >
                {s.label}
              </button>
            ))}
          </nav>
        </aside>

        {/* Content */}
        <main className="flex-1 min-w-0 max-w-3xl">
          {/* Mobile TOC */}
          <details className="lg:hidden mb-8 border bg-[#040c08]/40" style={{ borderColor: 'var(--border-main)' }}>
            <summary className="cursor-pointer px-4 py-3 text-[11px] font-black uppercase tracking-[0.3em] text-slate-400">On this page</summary>
            <div className="px-2 pb-3">
              {SECTIONS.map((s) => (
                <button key={s.id} onClick={() => scrollTo(s.id)} className="block w-full text-left px-3 py-2 text-[13px]" style={{ color: 'var(--text-muted)' }}>
                  {s.label}
                </button>
              ))}
            </div>
          </details>

          {/* Hero */}
          <div className="mb-10">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] font-black tracking-[0.2em] uppercase mb-4">
              <BookOpen className="w-3.5 h-3.5" /> Aeroponik Docs
            </div>
            <h1 className="text-4xl sm:text-5xl font-black uppercase tracking-tight leading-[1.05] mb-4" style={{ color: 'var(--text-main)' }}>
              Aeroponik Platform
            </h1>
            <p className="text-base sm:text-lg leading-relaxed" style={{ color: 'var(--text-muted)' }}>
              A production-grade, microservice-based control plane for precision aeroponic farming. This guide covers architecture, deployment, core concepts, the service catalogue, and how to operate the system end to end.
            </p>
          </div>

          {/* Overview */}
          <H2 id="overview">Overview</H2>
          <P>
            Aeroponik turns a fleet of <strong style={{ color: 'var(--text-main)' }}>ESP32 field nodes</strong> into a single, observable control system. Each node streams telemetry (pH, EC, temperature, humidity, root imagery) and accepts actuator commands (pumps, relays, misters). A resilient microservice backbone ingests that data, runs analytics and on-device AI vision, and lets operators drive actuation from a unified dashboard.
          </P>
          <P>
            The platform is built API-first: every capability — authentication, module management, telemetry, control, and analytics — is exposed as a documented service behind a single API gateway.
          </P>
          <Callout type="tip" title="Who this is for">
            Farm operators, DevOps engineers, and integrators who deploy, configure, or extend the Aeroponik control plane.
          </Callout>

          {/* Architecture */}
          <H2 id="architecture">Architecture</H2>
          <P>
            Aeroponik is composed of isolated Docker services that communicate through a message mesh and a central API gateway. There is no monolith and no single point of failure.
          </P>
          <Table
            head={['Layer', 'Components']}
            rows={[
              ['Edge', 'ESP32 nodes (sense + actuate), flashed firmware'],
              ['Gateway', 'Kong API Gateway, Cloudflare SSL tunnel'],
              ['Messaging', 'NATS (event bus), Mosquitto (MQTT)'],
              ['Services', 'auth, module, analytics, control, monitor, stream, ml, wsgateway (Go; ml is Python)'],
              ['Storage', 'MariaDB (per-service), TimescaleDB, Redis, MinIO'],
              ['Media', 'MediaMTX (RTSP) + stream service'],
              ['Observability', 'Prometheus, Grafana, exporters'],
            ]}
          />
          <Callout type="info" title="Why per-service databases">
            Each service owns its own MariaDB schema. This enforces bounded contexts, lets services scale and deploy independently, and contains schema changes to a single team.
          </Callout>

          {/* Quickstart */}
          <H2 id="quickstart">Quickstart</H2>
          <H3>Prerequisites</H3>
          <P>Docker Engine 20.10+ and Docker Compose v2, a Linux/macOS/Windows host with ~4 GB RAM, and at least one ESP32 node running the Aeroponik firmware.</P>
          <H3>Bring the stack up</H3>
          <CodeBlock code={`# From the repository root
cd Microservices
docker compose up -d

# Verify services are healthy
docker compose ps`} />
          <P>Once the stack is up, the Kong gateway exposes the dashboard and APIs. Open the application under the <Inline>/app</Inline> route and sign in with an administrator account.</P>
          <Callout type="warning" title="First run">
            Database schemas are migrated automatically on first boot. Allow 30–60 seconds for MariaDB/TimescaleDB to accept connections before the services report healthy.
          </Callout>
          <H3>Flash and pair a node</H3>
          <P>Flash the ESP32 firmware, then use the dashboard's <strong style={{ color: 'var(--text-main)' }}>Module → Manage / Pair Nodes</strong> flow to discover the device and link it to a module.</P>

          {/* Core Concepts */}
          <H2 id="concepts">Core Concepts</H2>
          <H3>Module</H3>
          <P>A logical grouping of nodes — typically one physical farm zone. Modules carry a name and description.</P>
          <H3>Node</H3>
          <P>An individual ESP32 device. Nodes report telemetry, respond to live commands, and are paired to exactly one module.</P>
          <H3>Tag</H3>
          <P>A mapping that turns a raw telemetry key (e.g. <Inline>telemetry.outputs.load1</Inline>) or an actuator output into a named, typed, labelled metric. Tags power the Analytics and Control views.</P>
          <Table
            head={['Tag kind', 'Purpose']}
            rows={[
              ['Telemetry tag', 'Plots a sensor reading in Analytics'],
              ['Actuator tag', 'Surfaces an output as a controllable target in Control'],
            ]}
          />
          <H3>Pairing</H3>
          <P>The process of linking a discovered node to a module. Unpaired nodes appear under discovery; paired nodes appear under the module.</P>

          {/* Services */}
          <H2 id="services">Services</H2>
          <P>All control-plane services are written in Go (the <Inline>ml</Inline> service is Python) and run as independent containers.</P>
          <Table
            head={['Service', 'Stack', 'Responsibility']}
            rows={[
              ['auth', 'Go', 'Identity, JWT issuance, role-based access control (RBAC)'],
              ['module', 'Go', 'Module & node registry, tag configuration, pairing'],
              ['analytics', 'Go', 'Aggregates telemetry into time-series metrics'],
              ['control', 'Go', 'Actuator commands, schedules, emergency stop'],
              ['monitor', 'Go', 'System health, status events, notifications'],
              ['stream', 'Go', 'Video/RTSP pipeline via MediaMTX'],
              ['ml', 'Python', 'YOLOv8 vision inference on node imagery'],
              ['wsgateway', 'Go', 'WebSocket gateway for live dashboard data'],
            ]}
          />
          <Callout type="note" title="Service discovery">
            Internal service-to-service calls travel over NATS and MQTT; external clients only ever talk to Kong.
          </Callout>

          {/* Data flow */}
          <H2 id="dataflow">Telemetry & Data Flow</H2>
          <P>Data moves through four stages, from the field to the actuator:</P>
          <Table
            head={['Stage', 'What happens']}
            rows={[
              ['1 · Sense', 'ESP32 nodes capture pH, EC, climate and root imagery at the edge'],
              ['2 · Stream', 'Kong routes requests and live WebSocket; MQTT and NATS carry device telemetry across the mesh'],
              ['3 · Analyze', 'The Analytics Service and ML vision (YOLOv8) surface trends and anomalies from raw telemetry'],
              ['4 · Actuate', 'The Control service drives pumps, relays and misters on operator command or schedule'],
            ]}
          />
          <CodeBlock code={`ESP32 ──MQTT/NATS──▶ module ──▶ analytics ──▶ dashboard
   │                                            │
   └──────────── WebSocket (wsgateway) ─────────┘──▶ live view`} />

          {/* Auth */}
          <H2 id="auth">Authentication & Authorization</H2>
          <P>Authentication is token-based. The <Inline>auth</Inline> service issues a JWT after a successful username/email + password login. Kong validates the token on every request.</P>
          <P>Authorization uses two roles:</P>
          <Table
            head={['Role', 'Capabilities']}
            rows={[
              ['admin', 'Manage modules, nodes, users, and all system settings'],
              ['operator', 'View telemetry and drive actuators within assigned modules'],
            ]}
          />
          <Callout type="warning" title="Session expiry">
            When the backend returns <Inline>401</Inline>, the dashboard automatically clears the local session and prompts you to sign in again. This is expected behaviour, not a logout.
          </Callout>

          {/* Dashboard */}
          <H2 id="dashboard">Using the Dashboard</H2>
          <P>The dashboard is organised into focused workspaces, available from the left sidebar:</P>
          <Table
            head={['Workspace', 'Use it to']}
            rows={[
              ['Analytics', 'Inspect aggregated telemetry, trends and histograms per node'],
              ['Control', 'Toggle outputs, schedule automatic actions, send emergency stop'],
              ['Module', 'Create modules, manage nodes, configure telemetry & actuator tags'],
              ['Account', 'Admin-only: manage users, roles and access'],
              ['Profile', 'Update your own profile and password'],
            ]}
          />
          <Callout type="tip" title="Live data">
            Open the node monitor to watch a device's telemetry stream in real time over WebSocket.
          </Callout>

          {/* API */}
          <H2 id="api">API Reference</H2>
          <P>All endpoints are served through Kong and grouped by service. Requests require a <Inline>Bearer</Inline> token unless noted. Full OpenAPI descriptions live with each service.</P>
          <H3>Auth</H3>
          <Table
            head={['Method', 'Path', 'Description']}
            rows={[
              ['POST', '/auth/login', 'Exchange credentials for a JWT'],
              ['POST', '/auth/register', 'Create an account (admin-gated)'],
              ['GET', '/auth/me', 'Return the current user'],
              ['POST', '/auth/logout', 'Invalidate the session'],
            ]}
          />
          <H3>Modules & Nodes</H3>
          <Table
            head={['Method', 'Path', 'Description']}
            rows={[
              ['GET', '/modules', 'List modules'],
              ['POST', '/modules', 'Create a module'],
              ['GET', '/modules/:id/nodes', 'List nodes in a module'],
              ['POST', '/modules/:id/nodes/:node/pair', 'Pair a node'],
              ['DELETE', '/modules/:id/nodes/:node', 'Delete a node record'],
            ]}
          />
          <H3>Telemetry, Control & Analytics</H3>
          <Table
            head={['Method', 'Path', 'Description']}
            rows={[
              ['GET', '/analytics/metrics', 'Query aggregated metrics'],
              ['POST', '/control/command', 'Send an actuator command'],
              ['WS', '/ws/nodes/:id/live', 'Subscribe to a node\'s live stream'],
            ]}
          />

          {/* Security */}
          <H2 id="security">Security</H2>
          <P>Aeroponik is hardened for untrusted networks:</P>
          <ul className="space-y-2 my-4 text-sm" style={{ color: 'var(--text-muted)' }}>
            <li className="flex items-start gap-2"><ShieldCheck className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" /> TLS everywhere — ingress is terminated behind an SSL-secured Cloudflare tunnel.</li>
            <li className="flex items-start gap-2"><ShieldCheck className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" /> Encrypted handshake between nodes and the gateway.</li>
            <li className="flex items-start gap-2"><ShieldCheck className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" /> RBAC enforced at Kong and within each service.</li>
            <li className="flex items-start gap-2"><ShieldCheck className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" /> Per-service databases limit the blast radius of any compromise.</li>
            <li className="flex items-start gap-2"><ShieldCheck className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" /> Edge failsafes cut power to pumps and relays when safety thresholds are breached.</li>
          </ul>

          {/* Operations */}
          <H2 id="operations">Operations & Observability</H2>
          <P>Every service exposes Prometheus metrics and structured logs. Grafana provides pre-built dashboards for service health, database and broker exporters.</P>
          <CodeBlock code={`# Inspect service health
docker compose logs -f module

# Scrape targets
curl -s localhost:9090/api/v1/targets | head`} />
          <Callout type="info" title="Exporters">
            Dedicated exporters ship for MariaDB (per service), Redis, NATS, Mosquitto, and Postgres/TimescaleDB, so every dependency is observable — not just the application.
          </Callout>

          <div className="mt-16 pt-6 border-t text-[11px] font-black uppercase tracking-widest" style={{ borderColor: 'var(--border-main)', color: 'var(--text-muted)' }}>
            © 2026 Aeroponik — Built for scale.
          </div>
        </main>
      </div>
    </div>
  );
}
