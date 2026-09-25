import React, { useMemo, useState } from "react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, CartesianGrid } from "recharts";
import { fmt } from "@/lib/api";
import { CHART_WINDOWS, DEFAULT_CHART_WINDOW_DAYS, windowByDays } from "./chartWindow";

const tooltipStyle = {
  background: "var(--bg-base)",
  border: "1px solid var(--bd-default)",
  borderRadius: 0,
  fontSize: 11,
  fontFamily: "Geist Mono, monospace",
};

function CustomTooltip({ active, payload, label, format }) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div style={tooltipStyle} data-testid="chart-tooltip">
      <div style={{ padding: "4px 8px", color: "var(--text-tertiary)", borderBottom: "1px solid var(--bd-default)" }}>
        {fmt.time(label)}
      </div>
      {payload.map((p, i) => (
        <div key={i} style={{ padding: "4px 8px", color: p.color }}>
          {format ? format(p.value) : p.value}
        </div>
      ))}
    </div>
  );
}

function ChartWindowToggle({ prefix, days, onChange }) {
  return (
    <div className="chart-window-toggle" data-testid={`${prefix}-window-toggle`}>
      {CHART_WINDOWS.map((d) => (
        <button
          key={d}
          type="button"
          className={`btn ${days === d ? "active" : ""}`}
          data-testid={`${prefix}-window-${d}`}
          onClick={() => onChange(d)}
        >
          {d}D
        </button>
      ))}
    </div>
  );
}

function WindowUnavailable({ testId, days }) {
  return (
    <div className="unavailable-block" data-testid={testId}>
      <span className="unavailable-label">Unavailable</span>
      <span className="kbd">empty {days}D window</span>
      <span>No points in the existing series for this range.</span>
    </div>
  );
}

export function EquityChart({ data, isSample = false }) {
  const [days, setDays] = useState(DEFAULT_CHART_WINDOW_DAYS);
  const windowed = useMemo(() => windowByDays(data, days), [data, days]);

  return (
    <div className="panel" data-testid="equity-panel" style={{ height: 320, display: "flex", flexDirection: "column" }}>
      <div className="panel-header">
        <span className="panel-title">
          Equity Curve · {days}D
          {isSample ? <span className="kbd" style={{ marginLeft: 8 }} data-testid="equity-sample-label">SAMPLE DATA</span> : null}
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <ChartWindowToggle prefix="equity" days={days} onChange={setDays} />
          <span className="kbd">{windowed.length} pts</span>
        </span>
      </div>
      <div style={{ flex: 1, padding: "8px 4px 4px 0", minHeight: 0 }}>
        {windowed.length === 0 ? (
          <WindowUnavailable testId="equity-window-unavailable" days={days} />
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={windowed} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="equityFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--sig-pos)" stopOpacity={0.18} />
                  <stop offset="100%" stopColor="var(--sig-pos)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="var(--bd-subtle)" strokeDasharray="0" vertical={false} />
              <XAxis
                dataKey="t"
                stroke="var(--text-tertiary)"
                tick={{ fontSize: 10, fontFamily: "Geist Mono", fill: "var(--text-tertiary)" }}
                tickFormatter={(t) => new Date(t).toLocaleDateString("en-GB", { day: "2-digit", month: "short" })}
                minTickGap={40}
              />
              <YAxis
                stroke="var(--text-tertiary)"
                tick={{ fontSize: 10, fontFamily: "Geist Mono", fill: "var(--text-tertiary)" }}
                tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
                domain={["auto", "auto"]}
                width={50}
              />
              <Tooltip content={<CustomTooltip format={fmt.money} />} cursor={{ stroke: "var(--bd-focus)", strokeDasharray: "2 2" }} />
              <Area
                type="monotone"
                dataKey="equity"
                stroke="var(--sig-pos)"
                strokeWidth={1.5}
                fill="url(#equityFill)"
                dot={false}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}

export function DrawdownChart({ data, maxDD, currentDD, isSample = false }) {
  const [days, setDays] = useState(DEFAULT_CHART_WINDOW_DAYS);
  const windowed = useMemo(() => windowByDays(data, days), [data, days]);

  return (
    <div className="panel" data-testid="drawdown-panel" style={{ height: 320, display: "flex", flexDirection: "column" }}>
      <div className="panel-header">
        <span className="panel-title">
          Drawdown · {days}D
          {isSample ? <span className="kbd" style={{ marginLeft: 8 }} data-testid="drawdown-sample-label">SAMPLE DATA</span> : null}
        </span>
        <span style={{ display: "flex", gap: 12, fontSize: 10, alignItems: "center" }}>
          <ChartWindowToggle prefix="drawdown" days={days} onChange={setDays} />
          <span style={{ color: "var(--text-tertiary)" }}>MAX</span>
          <span className="mono cell-neg" data-testid="dd-max">{fmt.pct(maxDD)}</span>
          <span style={{ color: "var(--text-tertiary)" }}>CUR</span>
          <span className="mono cell-neg" data-testid="dd-current">{fmt.pct(currentDD)}</span>
        </span>
      </div>
      <div style={{ flex: 1, padding: "8px 4px 4px 0", minHeight: 0 }}>
        {windowed.length === 0 ? (
          <WindowUnavailable testId="drawdown-window-unavailable" days={days} />
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={windowed} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="ddFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--sig-neg)" stopOpacity={0} />
                  <stop offset="100%" stopColor="var(--sig-neg)" stopOpacity={0.25} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="var(--bd-subtle)" strokeDasharray="0" vertical={false} />
              <XAxis
                dataKey="t"
                stroke="var(--text-tertiary)"
                tick={{ fontSize: 10, fontFamily: "Geist Mono", fill: "var(--text-tertiary)" }}
                tickFormatter={(t) => new Date(t).toLocaleDateString("en-GB", { day: "2-digit", month: "short" })}
                minTickGap={40}
              />
              <YAxis
                stroke="var(--text-tertiary)"
                tick={{ fontSize: 10, fontFamily: "Geist Mono", fill: "var(--text-tertiary)" }}
                tickFormatter={(v) => `${v.toFixed(1)}%`}
                width={50}
                domain={["dataMin", 0]}
              />
              <Tooltip content={<CustomTooltip format={(v) => `${v.toFixed(2)}%`} />} cursor={{ stroke: "var(--bd-focus)", strokeDasharray: "2 2" }} />
              <ReferenceLine y={0} stroke="var(--bd-focus)" strokeDasharray="2 2" />
              <Area
                type="monotone"
                dataKey="dd"
                stroke="var(--sig-neg)"
                strokeWidth={1.5}
                fill="url(#ddFill)"
                dot={false}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
