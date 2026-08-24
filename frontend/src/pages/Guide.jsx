import React from "react";
import PageShell from "@/pages/PageShell";
import { forgeFactoryLogo } from "@/assets/branding";

function Doc({ title, children, testId }) {
  return (
    <div className="panel doc-block" data-testid={testId}>
      <div className="panel-header">
        <span className="panel-title">{title}</span>
      </div>
      <div className="doc-body">{children}</div>
    </div>
  );
}

/** End-user Guide — English. Technical architecture lives in docs/ + README. */
export default function Guide() {
  return (
    <PageShell active="guide" testId="guide-page">
      <section className="doc-hero">
        <img
          src={forgeFactoryLogo}
          alt="Forge Factory Lab"
          className="doc-hero-logo"
          data-testid="guide-forge-logo"
        />
        <div>
          <h1>Guide</h1>
          <p className="mono">Sr. Atlas — User Guide</p>
        </div>
      </section>

      <Doc title="Why Sr. Atlas exists" testId="guide-why">
        <p>
          Trading is often sold as a get-rich-quick promise. In reality, most
          people who try end up acting on impulse — which, without realizing it,
          looks a lot like gambling. Studying it properly is hard, almost like
          understanding how a plane flies.
        </p>
        <p>
          Sr. Atlas was born out of a real need, not a business opportunity
          spotted from the outside: the need for something that helps{" "}
          <b>with every decision</b>, and helps you{" "}
          <b>learn from every decision</b> — not a tool that decides or trades
          for you.
        </p>
        <p>
          <b>What Sr. Atlas does NOT do:</b>
        </p>
        <ul>
          <li>It does not decide for you.</li>
          <li>It does not buy or sell anything on its own.</li>
          <li>It never touches your money or your orders.</li>
        </ul>
        <p>
          <b>What Sr. Atlas does:</b> it shows you the true state of your
          account, without filters or embellishment — even when that truth is
          uncomfortable (for example, warning you that data is outdated instead
          of pretending everything is fine). The decision is always yours; Atlas
          just helps you see clearly before you make it.
        </p>
      </Doc>

      <Doc title="The dashboard, element by element" testId="guide-panel">
        <p>
          <b>Top bar</b>
        </p>
        <ul>
          <li>
            <b>Tabs</b> (Overview, Strategies, Risk, Reports, Audit, About, Guide,
            Settings) — the different views of Atlas.
          </li>
          <li>
            <b>REFRESH FEED</b> — forces an immediate data update instead of
            waiting for the next automatic cycle.
          </li>
          <li>
            <b>v0.3.0 · [code version] · session-XXXX</b> — the exact installed
            version and current session identifier, useful when reporting
            problems.
          </li>
        </ul>

        <p>
          <b>Global stats bar</b>
        </p>
        <ul>
          <li>
            <b>TOTAL EQUITY</b> — your account&apos;s real value right now
            (balance plus/minus the result of open positions).
          </li>
          <li>
            <b>DAILY P&amp;L</b> — how much you&apos;ve gained or lost today, in
            value and percentage.
          </li>
          <li>
            <b>AVG DD</b> — the average &quot;drawdown&quot; (how much the
            account has fallen since its most recent peak) across monitored
            accounts.
          </li>
          <li>
            <b>OPEN POS</b> — number of currently open positions.
          </li>
          <li>
            <b>ACCOUNTS</b> — how many accounts are &quot;live&quot; (connected
            and receiving real data) out of the total configured.
          </li>
          <li>
            <b>ALERTS</b> — number of active alerts needing your attention.
          </li>
          <li>
            <b>UTC, date/time</b> — the system&apos;s reference clock (universal
            time, not local time).
          </li>
        </ul>

        <p>
          <b>&quot;MT5 Accounts&quot; table</b>
        </p>
        <p>
          One row per connected MT5 account. Columns: <b>Status</b>,{" "}
          <b>Account</b> (account number), <b>Broker</b>, <b>Strategy</b>{" "}
          (associated strategy name), <b>Balance</b>, <b>Equity</b> (real value,
          including open positions), <b>Daily P&amp;L</b>, <b>DD</b> (current
          drawdown), <b>POS</b> (open positions), <b>LEV</b> (leverage, e.g.{" "}
          <code>1:30</code>), <b>Margin %</b> (margin level — the higher it is,
          the more room you have before a broker &quot;stop out&quot;).
        </p>

        <p>
          <b>&quot;Risk&quot; section</b>
        </p>
        <p>
          Repeats the numbers for the selected account (Equity, Balance, Margin
          Used, Margin Lvl, Daily P&amp;L, Cur DD, Max DD, Leverage), plus:
        </p>
        <ul>
          <li>
            <b>Risk Limits</b> — three fields you define:{" "}
            <b>Max Daily Loss (%)</b>, <b>Max Position Size (lots)</b>,{" "}
            <b>Max Open Positions</b> — with a <b>Save Limits</b> button.
          </li>
        </ul>

        <p>
          <b>&quot;Sr. Atlas Supervision&quot; panel (right side)</b>
        </p>
        <ul>
          <li>
            Overall status badge: <b>OK</b> or <b>WARNING</b>, with a sentence
            explaining why (e.g. &quot;MT5 bridge is unavailable; displayed data
            comes from cache and may be outdated&quot;).
          </li>
          <li>Summary: Total Equity, Daily P&amp;L, Accounts Live, Active Alerts.</li>
          <li>
            <b>Core Services</b> — the status of each internal Atlas component,
            one by one:
            <ul>
              <li>
                <b>Backend</b> — the &quot;brain&quot; that serves the dashboard.
              </li>
              <li>
                <b>Store</b> — where the data is kept.
              </li>
              <li>
                <b>Bridge</b> — the direct connection to your MT5 terminal.
              </li>
              <li>
                <b>Dashboard</b> — the panel you&apos;re looking at right now.
              </li>
            </ul>
            Each shows <b>OK</b> (green) or <b>DOWN</b> (red). If Bridge is
            &quot;DOWN&quot;, the numbers you see come from a saved copy
            (cache), not live data — Atlas always warns you when this happens.
          </li>
          <li>
            <b>Generate Sr. Atlas Report</b> — button to create an account
            report.
          </li>
          <li>
            <b>Recent Reports</b> — list of reports already generated.
          </li>
        </ul>

        <p>
          <b>Charts, below</b>
        </p>
        <ul>
          <li>
            <b>Equity Curve · 90D</b> — your account&apos;s value over the last
            90 days.
          </li>
          <li>
            <b>Drawdown · 90D</b> — drawdowns from peak over the same period.
          </li>
        </ul>

        <p>
          <b>Trade history (bottom of Overview)</b>
        </p>
        <ul>
          <li>
            <b>Trade History</b> — list of your already-closed trades: symbol,
            side (buy/sell), lots, open/close time, duration in minutes, result
            (P&amp;L), and associated strategy. You can filter by symbol and
            side. At the top of the table: total net result (<b>NET</b>), win
            percentage (<b>WIN%</b>), and number of trades (<b>N</b>).
          </li>
        </ul>

        <p>
          <b>Alerts panel (right side)</b>
        </p>
        <ul>
          <li>
            <b>Alerts</b> — count of alerts by severity (red = critical, orange
            = warning, blue = info). Shows &quot;No alerts&quot; when
            there&apos;s nothing to flag.
          </li>
          <li>
            <b>System</b> — the technical &quot;pulse&quot; of the system:{" "}
            <b>API Latency</b>, <b>MT5 Bridge</b>, <b>Risk Engine</b>,{" "}
            <b>Telegram Notif</b>, <b>Last Heartbeat</b>,{" "}
            <b>Strategies Loaded</b>.
          </li>
        </ul>
      </Doc>

      <Doc title="The other tabs" testId="guide-tabs">
        <p>
          <b>Strategies</b>
        </p>
        <p>
          Groups your accounts by strategy instead of by individual account —
          useful if you ever have multiple accounts following the same approach.
          Shows, per strategy: associated accounts, how many are live, total
          equity, daily P&amp;L, open positions, average drawdown.
        </p>
        <p>
          <b>Risk</b>
        </p>
        <p>
          The same &quot;Risk&quot; section described above (Risk Limits), as
          its own page.
        </p>
        <p>
          <b>Reports</b>
        </p>
        <p>
          List of reports already generated via the &quot;Generate Sr. Atlas
          Report&quot; button, with status, message, and origin for each. Empty
          until you generate the first one.
        </p>
        <p>
          <b>Audit</b>
        </p>
        <p>
          A historical log of system events (Atlas&apos;s &quot;logbook&quot;) —
          separate from trade history. Empty until events are logged.
        </p>
        <p>
          <b>About</b>
        </p>
        <p>
          Brand presentation page — the Forge Factory Lab logo and principles
          (&quot;Knowledge, validation and truth come before automation&quot;)
          and Sr. Atlas&apos;s own. No functionality, identity only.
        </p>
        <p>
          <b>Settings</b>
        </p>
        <p>
          Where you connect (or change, anytime, without reinstalling) your MT5
          account:
        </p>
        <ul>
          <li>
            <b>MT5 Login</b> — your account number.
          </li>
          <li>
            <b>MT5 Password</b> — stored; leave blank to keep the current one.
          </li>
          <li>
            <b>Server / Broker</b> — your broker&apos;s server name (e.g.{" "}
            <code>PepperstoneUK-Demo</code>).
          </li>
          <li>
            <b>Terminal path</b> (optional) — where MT5 is installed; you usually
            don&apos;t need to touch this, Atlas finds it automatically.
          </li>
          <li>
            <b>Bridge port</b> — the technical port used for the connection (no
            need to change this unless you know exactly why).
          </li>
          <li>
            <b>Save &amp; Connect</b> — saves and connects.
          </li>
          <li>
            <b>Clear</b> — clears the fields.
          </li>
        </ul>
        <p>
          An indicator at the top always shows whether you&apos;re{" "}
          <b>Connected</b> or not, in real time.
        </p>
      </Doc>

      <Doc title="Before you start" testId="guide-prereqs">
        <p>You need:</p>
        <ol>
          <li>
            A MetaTrader 5 account (demo or real) already created, with login,
            password, and server name (e.g. <code>PepperstoneUK-Demo</code>).
          </li>
          <li>The MetaTrader 5 terminal installed on this computer.</li>
          <li>
            In the MT5 terminal: go to <b>Tools → Options → Expert Advisors</b>{" "}
            and enable <b>&quot;Allow algorithmic trading&quot;</b>. Without
            this, Sr. Atlas connects to your account but can&apos;t confirm
            everything is ready.
          </li>
        </ol>
      </Doc>

      <Doc title="How to connect your account" testId="guide-connect">
        <ol>
          <li>Open Sr. Atlas.</li>
          <li>
            Go to <b>Settings</b>.
          </li>
          <li>Enter your MT5 login, password, and server.</li>
          <li>
            Save. The dashboard should show your real data within seconds.
          </li>
        </ol>
        <p>
          You don&apos;t need to open the MT5 terminal manually first — Sr. Atlas
          handles that on its own.
        </p>
      </Doc>

      <Doc title="What the dashboard states mean" testId="guide-states">
        <div className="doc-table-wrap">
          <table className="doc-table">
            <thead>
              <tr>
                <th>State</th>
                <th>What it means</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>
                  <b>OK / Healthy</b>
                </td>
                <td>Everything connected and working normally.</td>
              </tr>
              <tr>
                <td>
                  <b>WARNING</b>
                </td>
                <td>
                  Connected, but something needs your attention — for example,
                  &quot;Allow algorithmic trading&quot; disabled in the
                  terminal.
                </td>
              </tr>
              <tr>
                <td>
                  <b>PAUSED</b>
                </td>
                <td>
                  Supervision is temporarily stopped — usually because the
                  connection to the MT5 terminal was interrupted.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p>
          Sr. Atlas never shows &quot;all healthy&quot; if your account
          connection is actually down — we&apos;d rather warn you than lie to you
          about your account&apos;s status.
        </p>
      </Doc>

      <Doc title="Common problems" testId="guide-troubleshoot">
        <p>
          <b>&quot;The dashboard isn&apos;t showing my data&quot;</b>
        </p>
        <ul>
          <li>Confirm the MT5 terminal is installed on this computer.</li>
          <li>
            Confirm &quot;Allow algorithmic trading&quot; is enabled (see
            above).
          </li>
          <li>Confirm your login/password/server in Settings.</li>
        </ul>
        <p>
          <b>
            &quot;A warning about automated trading being disabled appears&quot;
          </b>
        </p>
        <ul>
          <li>
            Go to the MT5 terminal → Tools → Options → Expert Advisors → enable
            &quot;Allow algorithmic trading&quot;.
          </li>
        </ul>
        <p>
          <b>&quot;I installed it but nothing opens in the browser&quot;</b>
        </p>
        <ul>
          <li>
            Wait a minute — the services may take a few seconds to start after
            installation.
          </li>
          <li>
            If it still doesn&apos;t open, try the &quot;Start Atlas&quot;
            shortcut in the Start menu.
          </li>
        </ul>
      </Doc>

      <Doc title="Where to get help" testId="guide-report">
        <p>
          If the sections above don&apos;t solve it, use the{" "}
          <b>&quot;Report Problem&quot;</b> button on the dashboard. It
          automatically attaches the system&apos;s health status and relevant
          logs — never your credentials — and sends it directly to Forge Factory
          Lab, with one click.
        </p>
        <p className="doc-footnote">
          This document explains what Sr. Atlas does and doesn&apos;t do. If
          anything here doesn&apos;t match what you see on screen, trust what you
          see over this text — and please let us know.
        </p>
      </Doc>
    </PageShell>
  );
}
