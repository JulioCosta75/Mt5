import React from "react";
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, CartesianGrid } from "recharts";
import { fmt } from "@/lib/api";

const tooltipStyle = {
  background: "#0A0A0A",
  border: "1px solid #27272A",
  borderRadius: 0,
  fontSize: 11,
  fontFamily: "Geist Mono, monospace",
};

function CustomTooltip({ active, payload, label, format }) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div style={tooltipStyle} data-testid="chart-tooltip">
      <div style={{ padding: "4px 8px", color: "#71717A", borderBottom: "1px solid #27272A" }}>
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

export function EquityChart({ data }) {
  return (
    <div className="panel" data-testid="equity-panel" style={{ height: 320, display: "flex", flexDirection: "column" }}>
      <div className="panel-header">
        <span className="panel-title">Equity Curve · 90D</span>
        <span className="kbd">{data?.length ?? 0} pts</span>
      </div>
      <div style={{ flex: 1, padding: "8px 4px 4px 0" }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="equityFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#22C55E" stopOpacity={0.18} />
                <stop offset="100%" stopColor="#22C55E" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#18181B" strokeDasharray="0" vertical={false} />
            <XAxis
              dataKey="t"
              stroke="#52525B"
              tick={{ fontSize: 10, fontFamily: "Geist Mono" }}
              tickFormatter={(t) => new Date(t).toLocaleDateString("en-GB", { day: "2-digit", month: "short" })}
              minTickGap={40}
            />
            <YAxis
              stroke="#52525B"
              tick={{ fontSize: 10, fontFamily: "Geist Mono" }}
              tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
              domain={["auto", "auto"]}
              width={50}
            />
            <Tooltip content={<CustomTooltip format={fmt.money} />} cursor={{ stroke: "#3F3F46", strokeDasharray: "2 2" }} />
            <Area
              type="monotone"
              dataKey="equity"
              stroke="#22C55E"
              strokeWidth={1.5}
              fill="url(#equityFill)"
              dot={false}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function DrawdownChart({ data, maxDD, currentDD }) {
  return (
    <div className="panel" data-testid="drawdown-panel" style={{ height: 320, display: "flex", flexDirection: "column" }}>
      <div className="panel-header">
        <span className="panel-title">Drawdown · 90D</span>
        <span style={{ display: "flex", gap: 12, fontSize: 10 }}>
          <span style={{ color: "var(--text-tertiary)" }}>MAX</span>
          <span className="mono cell-neg" data-testid="dd-max">{fmt.pct(maxDD)}</span>
          <span style={{ color: "var(--text-tertiary)" }}>CUR</span>
          <span className="mono cell-neg" data-testid="dd-current">{fmt.pct(currentDD)}</span>
        </span>
      </div>
      <div style={{ flex: 1, padding: "8px 4px 4px 0" }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="ddFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#EF4444" stopOpacity={0} />
                <stop offset="100%" stopColor="#EF4444" stopOpacity={0.25} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#18181B" strokeDasharray="0" vertical={false} />
            <XAxis
              dataKey="t"
              stroke="#52525B"
              tick={{ fontSize: 10, fontFamily: "Geist Mono" }}
              tickFormatter={(t) => new Date(t).toLocaleDateString("en-GB", { day: "2-digit", month: "short" })}
              minTickGap={40}
            />
            <YAxis
              stroke="#52525B"
              tick={{ fontSize: 10, fontFamily: "Geist Mono" }}
              tickFormatter={(v) => `${v.toFixed(1)}%`}
              width={50}
              domain={["dataMin", 0]}
            />
            <Tooltip content={<CustomTooltip format={(v) => `${v.toFixed(2)}%`} />} cursor={{ stroke: "#3F3F46", strokeDasharray: "2 2" }} />
            <ReferenceLine y={0} stroke="#3F3F46" strokeDasharray="2 2" />
            <Area
              type="monotone"
              dataKey="dd"
              stroke="#EF4444"
              strokeWidth={1.5}
              fill="url(#ddFill)"
              dot={false}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
