import React, { useState, useEffect, useMemo, useCallback } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";
import {
  Thermometer, Gauge, Zap, Timer, Radio, AlertTriangle, CheckCircle2, Cog,
  Wind, MoveHorizontal, Wifi, WifiOff, Clock, ChevronRight, Cpu, Server, ListTree,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Config -- this dashboard is a real client of the FastAPI backend (api/app.py).
// It no longer generates any data itself; every number on screen comes from
// a live poll of these endpoints. Run the backend locally (see its README)
// and adjust API_BASE_URL if it's not on the default port.
// ---------------------------------------------------------------------------

const API_BASE_URL = "http://localhost:8000";
const POLL_MS = 2000;
const HISTORY_LEN = 24;

const MACHINE_META = {
  "M-101": { icon: Cog },
  "P-204": { icon: Wind },
  "C-310": { icon: Server },
  "CV-05": { icon: MoveHorizontal },
};

const COLORS = {
  bg: "#10151A",
  panel: "#1A2129",
  panelAlt: "#1F2933",
  line: "#2C3945",
  textPrimary: "#E7ECF0",
  textMuted: "#7F8FA0",
  healthy: "#2DD4B8",
  warning: "#F4A72E",
  critical: "#F0505A",
  accent: "#4E8DF2",
};

const STATUS_META = {
  healthy: { label: "NOMINAL", color: COLORS.healthy },
  warning: { label: "DEGRADED", color: COLORS.warning },
  critical: { label: "AT RISK", color: COLORS.critical },
};

function statusColor(status) {
  return (STATUS_META[status] || STATUS_META.healthy).color;
}

function nowLabel() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

// ---------------------------------------------------------------------------
// Gauge: analog-style arc dial
// ---------------------------------------------------------------------------

function ArcGauge({ value, color, size = 108 }) {
  const stroke = 9;
  const r = (size - stroke) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const startAngle = -220;
  const sweep = 260;
  const clamped = Math.max(0, Math.min(100, value ?? 0));

  const polar = (angleDeg, radius) => {
    const rad = (angleDeg * Math.PI) / 180;
    return { x: cx + radius * Math.cos(rad), y: cy + radius * Math.sin(rad) };
  };
  const arcPath = (fromDeg, toDeg, radius) => {
    const start = polar(fromDeg, radius);
    const end = polar(toDeg, radius);
    const largeArc = Math.abs(toDeg - fromDeg) > 180 ? 1 : 0;
    return `M ${start.x} ${start.y} A ${radius} ${radius} 0 ${largeArc} 1 ${end.x} ${end.y}`;
  };

  const valueAngle = startAngle + (clamped / 100) * sweep;
  const ticks = Array.from({ length: 11 }, (_, i) => startAngle + (i / 10) * sweep);

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <path d={arcPath(startAngle, startAngle + sweep, r)} fill="none" stroke={COLORS.line} strokeWidth={stroke} strokeLinecap="round" />
      <path d={arcPath(startAngle, valueAngle, r)} fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round" />
      {ticks.map((ang, i) => {
        const p1 = polar(ang, r - stroke / 2 - 2);
        const p2 = polar(ang, r - stroke / 2 - 7);
        return <line key={i} x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y} stroke={COLORS.textMuted} strokeWidth={1} opacity={0.5} />;
      })}
      <text x={cx} y={cy - 2} textAnchor="middle" fontSize={22} fontWeight={700} fill={COLORS.textPrimary} fontFamily="ui-monospace, monospace">
        {Math.round(clamped)}
      </text>
      <text x={cx} y={cy + 16} textAnchor="middle" fontSize={9} letterSpacing={1.5} fill={COLORS.textMuted} fontFamily="ui-monospace, monospace">
        HEALTH
      </text>
    </svg>
  );
}

function MiniSpark({ data, color }) {
  return (
    <div style={{ width: "100%", height: 34 }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 2, right: 2, left: 2, bottom: 2 }}>
          <Line type="monotone" dataKey="rotational_speed" stroke={color} strokeWidth={1.75} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function PredictiveMaintenanceDashboard() {
  const [machines, setMachines] = useState([]);
  const [histories, setHistories] = useState({}); // machine_id -> array of readings
  const [selectedId, setSelectedId] = useState("P-204");
  const [alerts, setAlerts] = useState([]);
  const [clock, setClock] = useState(nowLabel());
  const [connected, setConnected] = useState(null); // null = not yet checked

  const fetchAll = useCallback(async () => {
    try {
      const [machinesRes, alertsRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/machines`),
        fetch(`${API_BASE_URL}/api/alerts?limit=30`),
      ]);
      if (!machinesRes.ok || !alertsRes.ok) throw new Error("bad response");
      const machinesData = await machinesRes.json();
      const alertsData = await alertsRes.json();

      setMachines(machinesData);
      setAlerts(alertsData);
      setConnected(true);

      if (machinesData.length && !machinesData.find((m) => m.machine_id === selectedId)) {
        setSelectedId(machinesData[0].machine_id);
      }

      const sel = selectedId || (machinesData[0] && machinesData[0].machine_id);
      if (sel) {
        const histRes = await fetch(`${API_BASE_URL}/api/machines/${sel}/history?limit=${HISTORY_LEN}`);
        if (histRes.ok) {
          const histData = await histRes.json();
          setHistories((prev) => ({ ...prev, [sel]: histData }));
        }
      }
    } catch (e) {
      setConnected(false);
    }
  }, [selectedId]);

  useEffect(() => {
    fetchAll();
    const dataInterval = setInterval(fetchAll, POLL_MS);
    const clockInterval = setInterval(() => setClock(nowLabel()), 1000);
    return () => {
      clearInterval(dataInterval);
      clearInterval(clockInterval);
    };
  }, [fetchAll]);

  const selected = machines.find((m) => m.machine_id === selectedId);
  const selectedHistory = histories[selectedId] || [];

  const fleetHealth = machines.length
    ? Math.round(machines.reduce((s, m) => s + (m.health?.health ?? 0), 0) / machines.length)
    : 0;
  const atRiskCount = machines.filter((m) => m.health && m.health.status !== "healthy").length;

  const chartData = useMemo(
    () =>
      selectedHistory.map((h, i) => ({
        idx: i,
        rotational_speed: h.rotational_speed,
        torque: h.torque,
        process_temperature: Number((h.process_temperature - 273.15).toFixed(1)), // K -> °C
      })),
    [selectedHistory]
  );

  if (connected === false) {
    return (
      <div style={{ background: COLORS.bg, minHeight: "100vh", color: COLORS.textPrimary, display: "flex",
        alignItems: "center", justifyContent: "center", fontFamily: "'Segoe UI', ui-sans-serif, sans-serif" }}>
        <div style={{ textAlign: "center", maxWidth: 420 }}>
          <WifiOff size={32} color={COLORS.critical} style={{ marginBottom: 12 }} />
          <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>Backend not reachable</div>
          <div style={{ color: COLORS.textMuted, fontSize: 13, lineHeight: 1.6 }}>
            This dashboard reads live data from the FastAPI backend at{" "}
            <span style={{ fontFamily: "monospace", color: COLORS.accent }}>{API_BASE_URL}</span>.
            Start the backend (simulator + ingestion + inference + <span style={{ fontFamily: "monospace" }}>uvicorn api.app:app --port 8000</span>) and this page will connect automatically.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ background: COLORS.bg, minHeight: "100vh", color: COLORS.textPrimary,
      fontFamily: "'Segoe UI', ui-sans-serif, system-ui, sans-serif" }} className="w-full">

      <div style={{ borderBottom: `1px solid ${COLORS.line}`, background: COLORS.panel }}
        className="px-5 py-3 flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <div style={{ background: COLORS.accent }} className="w-9 h-9 rounded-sm flex items-center justify-center">
            <Cpu size={18} color="#0B0F13" />
          </div>
          <div>
            <div style={{ letterSpacing: 2 }} className="text-xs font-bold uppercase text-white">PMS&nbsp;/&nbsp;IoT</div>
            <div style={{ color: COLORS.textMuted }} className="text-[11px]">Predictive Maintenance Console — live backend data</div>
          </div>
        </div>
        <div className="flex items-center gap-5 text-xs">
          <div className="flex items-center gap-1.5" style={{ color: connected ? COLORS.healthy : COLORS.textMuted }}>
            {connected ? <Wifi size={14} /> : <WifiOff size={14} />}
            <span className="font-mono">{connected ? "API CONNECTED" : "CONNECTING..."}</span>
          </div>
          <div className="flex items-center gap-1.5" style={{ color: COLORS.textMuted }}>
            <Clock size={14} /><span className="font-mono">{clock}</span>
          </div>
        </div>
      </div>

      <div className="p-5 grid grid-cols-1 xl:grid-cols-12 gap-5">
        <div className="xl:col-span-8 flex flex-col gap-5">
          <div className="grid grid-cols-3 gap-4">
            <SummaryCard label="FLEET HEALTH" value={`${fleetHealth}%`} color={statusColor(fleetHealth >= 75 ? "healthy" : fleetHealth >= 50 ? "warning" : "critical")} />
            <SummaryCard label="DEVICES ONLINE" value={`${machines.length} / 4`} color={COLORS.accent} />
            <SummaryCard label="ASSETS AT RISK" value={String(atRiskCount)} color={atRiskCount > 0 ? COLORS.warning : COLORS.healthy} />
          </div>

          <div>
            <SectionLabel icon={ListTree} text="EQUIPMENT FLEET (LIVE FROM BACKEND)" />
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-2">
              {machines.map((m) => {
                const status = m.health?.status || "healthy";
                const meta = STATUS_META[status];
                const Icon = (MACHINE_META[m.machine_id] || {}).icon || Cog;
                const isSel = m.machine_id === selectedId;
                const hist = histories[m.machine_id] || [];
                return (
                  <button key={m.machine_id} onClick={() => setSelectedId(m.machine_id)}
                    style={{ background: COLORS.panel, border: `1px solid ${isSel ? meta.color : COLORS.line}`, textAlign: "left" }}
                    className="rounded-sm p-4 flex items-center gap-4 hover:opacity-90 transition-opacity">
                    <ArcGauge value={m.health?.health} color={meta.color} size={84} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <Icon size={14} color={COLORS.textMuted} />
                        <span className="text-[13px] font-semibold truncate">{m.name}</span>
                      </div>
                      <div style={{ color: COLORS.textMuted }} className="text-[11px] font-mono mt-0.5">
                        {m.machine_id} · Type {m.dataset_type} · {m.unit}
                      </div>
                      <div className="flex items-center gap-2 mt-2 flex-wrap">
                        <span style={{ color: meta.color, borderColor: meta.color }}
                          className="text-[10px] font-mono uppercase border rounded-sm px-1.5 py-0.5 tracking-wide">
                          {meta.label}
                        </span>
                        {m.health?.rul_minutes != null && (
                          <span style={{ color: COLORS.textMuted }} className="text-[10px] font-mono">
                            tool life ~{Math.round(m.health.rul_minutes)}min
                          </span>
                        )}
                      </div>
                      {hist.length > 1 && <div className="mt-2"><MiniSpark data={hist} color={meta.color} /></div>}
                    </div>
                    <ChevronRight size={16} color={COLORS.textMuted} />
                  </button>
                );
              })}
            </div>
          </div>

          <div style={{ background: COLORS.panel, border: `1px solid ${COLORS.line}` }} className="rounded-sm p-4">
            <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
              <SectionLabel icon={Gauge} text={`SENSOR TREND — ${selectedId || "—"}`} />
              {selected?.health && (
                <span style={{ color: statusColor(selected.health.status) }} className="text-[11px] font-mono uppercase">
                  {STATUS_META[selected.health.status]?.label}
                </span>
              )}
            </div>

            {selected?.latest_reading && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                <ReadingTile icon={Gauge} label="Rotational Speed" value={selected.latest_reading.rotational_speed} unit="rpm" />
                <ReadingTile icon={Zap} label="Torque" value={selected.latest_reading.torque?.toFixed(1)} unit="Nm" />
                <ReadingTile icon={Thermometer} label="Process Temp" value={(selected.latest_reading.process_temperature - 273.15).toFixed(1)} unit="°C" />
                <ReadingTile icon={Timer} label="Tool Wear" value={selected.latest_reading.tool_wear} unit="min" />
              </div>
            )}

            <div style={{ width: "100%", height: 220 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 4, right: 12, left: -12, bottom: 0 }}>
                  <CartesianGrid stroke={COLORS.line} strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="idx" tick={{ fill: COLORS.textMuted, fontSize: 10 }} axisLine={{ stroke: COLORS.line }} tickLine={false} />
                  <YAxis tick={{ fill: COLORS.textMuted, fontSize: 10 }} axisLine={{ stroke: COLORS.line }} tickLine={false} />
                  <Tooltip contentStyle={{ background: COLORS.panelAlt, border: `1px solid ${COLORS.line}`, fontSize: 11 }} labelStyle={{ color: COLORS.textMuted }} />
                  <Line type="monotone" dataKey="rotational_speed" name="Rotational Speed (rpm)" stroke={COLORS.accent} strokeWidth={2} dot={false} isAnimationActive={false} />
                  <Line type="monotone" dataKey="torque" name="Torque (Nm)" stroke={COLORS.warning} strokeWidth={2} dot={false} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        <div className="xl:col-span-4 flex flex-col gap-5">
          <div style={{ background: COLORS.panel, border: `1px solid ${COLORS.line}` }} className="rounded-sm p-4">
            <SectionLabel icon={Radio} text="DATA PIPELINE" />
            <div className="mt-3 flex flex-col gap-2 text-[11px] font-mono">
              {[
                ["Real Data (AI4I2020)", "replayed via MQTT"],
                ["MQTT Broker", "QoS 1 · topic: plant/line2/#"],
                ["Ingest + Real ML Model", "RandomForest + IsolationForest"],
                ["This Dashboard", `polling ${API_BASE_URL}`],
              ].map(([label, sub], i, arr) => (
                <div key={label}>
                  <div className="flex items-center gap-2">
                    <span style={{ background: COLORS.accent }} className="w-1.5 h-1.5 rounded-full flex-shrink-0" />
                    <span className="text-white font-semibold">{label}</span>
                  </div>
                  <div style={{ color: COLORS.textMuted, marginLeft: 14 }}>{sub}</div>
                  {i < arr.length - 1 && <div style={{ borderLeft: `1px solid ${COLORS.line}`, height: 10, marginLeft: 2.5 }} />}
                </div>
              ))}
            </div>
          </div>

          <div style={{ background: COLORS.panel, border: `1px solid ${COLORS.line}` }} className="rounded-sm p-4 flex-1">
            <SectionLabel icon={AlertTriangle} text="EVENT LOG (LIVE)" />
            <div className="mt-3 flex flex-col gap-2.5 max-h-[520px] overflow-y-auto pr-1">
              {alerts.length === 0 && <div style={{ color: COLORS.textMuted }} className="text-[11px]">No alerts yet.</div>}
              {alerts.map((a) => (
                <div key={a.id} className="flex items-start gap-2 text-[11px]">
                  {a.severity === "critical" && <AlertTriangle size={13} color={COLORS.critical} className="mt-0.5 flex-shrink-0" />}
                  {a.severity === "warning" && <AlertTriangle size={13} color={COLORS.warning} className="mt-0.5 flex-shrink-0" />}
                  <div>
                    <span style={{ color: COLORS.textMuted }} className="font-mono">{new Date(a.ts).toLocaleTimeString()}</span>{" "}
                    <span style={{ color: COLORS.textPrimary }}>{a.message}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div style={{ borderTop: `1px solid ${COLORS.line}`, color: COLORS.textMuted }} className="px-5 py-3 text-[10px] font-mono text-center">
        Live client of the Predictive Maintenance backend API. Sensor values are real AI4I2020 dataset rows replayed over MQTT pending physical sensor deployment.
      </div>
    </div>
  );
}

function SummaryCard({ label, value, color }) {
  return (
    <div style={{ background: COLORS.panel, border: `1px solid ${COLORS.line}` }} className="rounded-sm p-4">
      <div style={{ color: COLORS.textMuted, letterSpacing: 1.5 }} className="text-[10px] font-mono uppercase">{label}</div>
      <div style={{ color }} className="text-2xl font-bold font-mono mt-1">{value}</div>
    </div>
  );
}

function SectionLabel({ icon: Icon, text }) {
  return (
    <div className="flex items-center gap-2">
      <Icon size={13} color={COLORS.textMuted} />
      <span style={{ color: COLORS.textMuted, letterSpacing: 1.5 }} className="text-[10px] font-mono uppercase">{text}</span>
    </div>
  );
}

function ReadingTile({ icon: Icon, label, value, unit }) {
  return (
    <div style={{ background: COLORS.panelAlt, border: `1px solid ${COLORS.line}` }} className="rounded-sm p-3">
      <div className="flex items-center gap-1.5" style={{ color: COLORS.textMuted }}>
        <Icon size={12} /><span className="text-[10px] font-mono uppercase">{label}</span>
      </div>
      <div className="font-mono mt-1">
        <span className="text-lg font-bold text-white">{value}</span>
        <span style={{ color: COLORS.textMuted }} className="text-[11px]"> {unit}</span>
      </div>
    </div>
  );
}
