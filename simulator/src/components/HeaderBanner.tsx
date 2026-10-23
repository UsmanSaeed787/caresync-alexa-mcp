"use client";

import React from "react";
import { AlertTriangle, Radio, RefreshCw, Server, ShieldCheck, Sparkles } from "lucide-react";
import { HealthStatus } from "@/lib/types";

interface HeaderBannerProps {
  health: HealthStatus | null;
  loading: boolean;
  onRefresh: () => void;
}

export const HeaderBanner: React.FC<HeaderBannerProps> = ({
  health,
  loading,
  onRefresh,
}) => {
  const isHealthy = health?.status === "healthy";

  return (
    <header className="border-b border-slate-200 bg-white/95 sticky top-0 z-30 shadow-sm backdrop-blur">
      {/* 1. Permanent Safety Disclaimer Banner */}
      <div className="bg-amber-500 text-amber-950 px-4 py-1.5 text-xs font-semibold flex items-center justify-between border-b border-amber-600/20">
        <div className="flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 text-amber-950 shrink-0" />
          <span>
            <strong>PROTOTYPE SAFETY NOTICE:</strong> Strictly synthetic, fictional patient data.
            Does not diagnose, triage, prescribe, or provide medical advice. Human approval required for all actions.
          </span>
        </div>
        <span className="hidden md:inline-block bg-amber-600/30 px-2 py-0.5 rounded text-[11px] font-mono tracking-wide">
          SYNTHETIC TEST ENVIRONMENT
        </span>
      </div>

      {/* 2. Main Title & Status Bar */}
      <div className="max-w-7xl mx-auto px-4 py-3 sm:px-6 lg:px-8 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-sky-500 flex items-center justify-center text-white shadow-md shadow-indigo-500/20">
            <Radio className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-xl font-bold text-slate-900 tracking-tight">
                CareSync
              </h1>
              <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-200">
                <Sparkles className="w-3 h-3 mr-0.5 text-indigo-500" />
                Alexa+ Simulation
              </span>
              <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-slate-100 text-slate-600 border border-slate-200">
                v0.1.0
              </span>
            </div>
            <p className="text-xs text-slate-500">
              Voice-First Synthetic Hospital Discharge Follow-Up Workflow • Streamable HTTP MCP
            </p>
          </div>
        </div>

        {/* 3. System Connection Pills & Refresh */}
        <div className="flex items-center space-x-3 text-xs">
          {/* MCP Protocol Pill */}
          <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-100 border border-slate-200 text-slate-700">
            <Server className="w-3.5 h-3.5 text-slate-500" />
            <span className="font-medium">MCP Streamable:</span>
            <span className="font-mono text-indigo-600">{health?.mcp_endpoint || "/mcp"}</span>
          </div>

          {/* Backend Status Indicator */}
          <div
            className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg border font-medium transition-colors ${
              isHealthy
                ? "bg-emerald-50 border-emerald-200 text-emerald-800"
                : "bg-rose-50 border-rose-200 text-rose-800"
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                isHealthy ? "bg-emerald-500 animate-pulse" : "bg-rose-500"
              }`}
            />
            <span>
              {health ? (isHealthy ? "Backend Connected" : "Backend Degraded") : "Connecting..."}
            </span>
            {isHealthy && <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 ml-1" />}
          </div>

          {/* Refresh Action */}
          <button
            onClick={onRefresh}
            disabled={loading}
            className="p-2 rounded-lg border border-slate-200 hover:bg-slate-100 text-slate-600 hover:text-slate-900 transition-colors disabled:opacity-50"
            title="Refresh live server data"
            aria-label="Refresh live server data"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-indigo-600" : ""}`} />
          </button>
        </div>
      </div>
    </header>
  );
};
