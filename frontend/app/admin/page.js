"use client";

import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function StatCard({ label, value }) {
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900 p-4">
      <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-white">{value}</div>
    </div>
  );
}

export default function AdminPage() {
  const [secret, setSecret] = useState("");
  const [authed, setAuthed] = useState(false);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const fetchStats = async (secretValue) => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_URL}/admin/stats`, {
        headers: { "X-Admin-Secret": secretValue },
      });
      if (!res.ok) {
        throw new Error(res.status === 401 ? "Invalid admin secret." : "Failed to load stats.");
      }
      const data = await res.json();
      setStats(data);
      setAuthed(true);
    } catch (err) {
      setError(err.message);
      setAuthed(false);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    fetchStats(secret);
  };

  if (!authed) {
    return (
      <main className="flex min-h-screen items-center justify-center px-4">
        <form
          onSubmit={handleSubmit}
          className="w-full max-w-sm rounded-lg border border-slate-700 bg-slate-900 p-6"
        >
          <h1 className="mb-4 text-xl font-semibold text-white">Admin Access</h1>
          <input
            type="password"
            value={secret}
            onChange={(e) => setSecret(e.target.value)}
            placeholder="Admin secret"
            className="mb-3 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-indigo-500 focus:outline-none"
          />
          {error && <p className="mb-3 text-sm text-red-400">{error}</p>}
          <button
            type="submit"
            disabled={loading || !secret}
            className="w-full rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            {loading ? "Checking..." : "Enter"}
          </button>
        </form>
      </main>
    );
  }

  return (
    <main className="min-h-screen px-4 py-10">
      <div className="mx-auto max-w-3xl">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-white">Analytics Dashboard</h1>
          <button
            onClick={() => fetchStats(secret)}
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm hover:bg-slate-700"
          >
            Refresh
          </button>
        </div>

        {stats && (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <StatCard label="Total Queries" value={stats.total_queries} />
            <StatCard
              label="Avg Response Time"
              value={`${stats.average_response_time_ms} ms`}
            />
            <StatCard label="Error Rate" value={`${stats.error_rate_percent}%`} />
            <StatCard label="Queries (Last Hour)" value={stats.queries_last_hour} />
          </div>
        )}

        {stats && (
          <div className="mt-6 rounded-lg border border-slate-700 bg-slate-900 p-4">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
              Queries by Endpoint
            </h2>
            <div className="space-y-2">
              {Object.entries(stats.queries_by_endpoint).map(([endpoint, count]) => (
                <div key={endpoint} className="flex items-center justify-between text-sm">
                  <span className="font-mono text-slate-300">{endpoint}</span>
                  <span className="text-slate-100">{count}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
