"use client";

import { useEffect, useState } from "react";
import ChatInterface from "../components/ChatInterface";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function HomePage() {
  const [status, setStatus] = useState("checking");

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_URL}/health`)
      .then((res) => {
        if (!cancelled) setStatus(res.ok ? "online" : "offline");
      })
      .catch(() => {
        if (!cancelled) setStatus("offline");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main className="min-h-screen px-4 py-10">
      <div className="mx-auto mb-8 max-w-3xl text-center">
        <h1 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
          AI Dev Mentor
        </h1>
        <p className="mt-2 text-slate-400">
          Your AI pair programmer for generating, reviewing, and debugging code.
        </p>
        <div className="mt-4 inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-xs">
          <span
            className={`h-2 w-2 rounded-full ${
              status === "online"
                ? "bg-emerald-400"
                : status === "offline"
                ? "bg-red-500"
                : "bg-amber-400"
            }`}
          />
          <span className="text-slate-300">
            Backend:{" "}
            {status === "checking"
              ? "checking..."
              : status === "online"
              ? "connected"
              : "unreachable"}
          </span>
        </div>
      </div>

      <ChatInterface />
    </main>
  );
}
