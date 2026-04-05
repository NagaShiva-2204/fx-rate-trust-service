import React, { useEffect, useState } from "react";

const DEFAULT_BASE = "USD";
const DEFAULT_SYMBOLS = ["EUR", "GBP", "INR", "JPY", "AUD", "CAD"];

const API_URL = "http://localhost:8000/api/rates";

function formatDate(value) {
  if (!value) return "Unknown";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown";
  return date.toLocaleString();
}

export default function App() {
  const [base, setBase] = useState(DEFAULT_BASE);
  const [symbols, setSymbols] = useState(DEFAULT_SYMBOLS);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchRates = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        base,
        symbols: symbols.join(",")
      });
      const response = await fetch(`${API_URL}?${params.toString()}`);
      if (!response.ok) {
        throw new Error(`API returned ${response.status}`);
      }
      const payload = await response.json();
      setData(payload);
    } catch (err) {
      setError(err.message || "Failed to load rates.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRates();
    const interval = setInterval(fetchRates, 120000);
    return () => clearInterval(interval);
  }, [base, symbols.join(",")]);

  return (
    <div className="app">
      <div className="currency-float" aria-hidden="true">
        <span className="note usd" />
        <span className="note eur" />
        <span className="note gbp" />
        <span className="note jpy" />
        <span className="note inr" />
        <span className="note aud" />
      </div>
      <header className="hero">
        <div>
          <p className="eyebrow">Free Tier FX Snapshot</p>
          <h1>Trustable exchange rates for everyday decisions</h1>
          <p className="subhead">
            We blend multiple public sources, show freshness, and stay resilient
            when an API goes down.
          </p>
        </div>
        <div className="controls">
          <label>
            Base currency
            <select value={base} onChange={(e) => setBase(e.target.value)}>
              {["USD", "EUR", "GBP", "INR"].map((code) => (
                <option key={code} value={code}>
                  {code}
                </option>
              ))}
            </select>
          </label>
        </div>
      </header>

      <main className="card">
        {loading && <p className="status">Loading latest rates...</p>}
        {error && (
          <div className="status error">
            <p>We could not refresh rates right now.</p>
            <p className="muted">{error}</p>
          </div>
        )}
        {!loading && data && (
          <>
            <div className="meta">
              <div>
                <p className="label">Data freshness</p>
                <p className={`pill ${data.freshness || "unknown"}`}>
                  {data.freshness || "unknown"}
                </p>
              </div>
              <div>
                <p className="label">As of</p>
                <p>{formatDate(data.as_of || data.fetched_at)}</p>
              </div>
              <div>
                <p className="label">Sources</p>
                <p>{(data.sources || []).join(", ") || "Unknown"}</p>
              </div>
            </div>
            {data.warnings && data.warnings.length > 0 && (
              <div className="status warning">
                {data.warnings.map((warning) => (
                  <p key={warning}>{warning}</p>
                ))}
              </div>
            )}
            <div className="rates">
              {symbols.map((symbol) => (
                <div className="rate" key={symbol}>
                  <p className="code">{symbol}</p>
                  <p className="value">
                    {data.rates && data.rates[symbol]
                      ? data.rates[symbol].toFixed(4)
                      : "—"}
                  </p>
                </div>
              ))}
            </div>
          </>
        )}
      </main>

      <footer className="footer">
        <p>
          Paid plan offers real-time rates, historical charts, and guaranteed
          uptime.
        </p>
      </footer>
    </div>
  );
}
