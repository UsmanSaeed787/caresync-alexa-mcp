"use client";

import React, { useState } from "react";
import {
  Activity,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  History,
  ShieldCheck,
  User,
  XCircle,
} from "lucide-react";
import { AuditEvent } from "@/lib/types";

interface AuditTrailProps {
  events: AuditEvent[];
  loading: boolean;
}

export const AuditTrail: React.FC<AuditTrailProps> = ({ events, loading }) => {
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null);

  const getActionBadge = (action: string) => {
    switch (action) {
      case "PROPOSAL_CREATED":
        return {
          label: "PROPOSAL CREATED",
          bg: "bg-sky-50 text-sky-800 border-sky-200",
          icon: <Activity className="w-3 h-3 text-sky-600" />,
        };
      case "PROPOSAL_APPROVED":
        return {
          label: "PROPOSAL APPROVED",
          bg: "bg-emerald-50 text-emerald-800 border-emerald-200",
          icon: <CheckCircle2 className="w-3 h-3 text-emerald-600" />,
        };
      case "PROPOSAL_REJECTED":
        return {
          label: "PROPOSAL REJECTED",
          bg: "bg-rose-50 text-rose-800 border-rose-200",
          icon: <XCircle className="w-3 h-3 text-rose-600" />,
        };
      case "TASK_CREATED":
        return {
          label: "TASK PERSISTED",
          bg: "bg-indigo-50 text-indigo-800 border-indigo-200",
          icon: <ShieldCheck className="w-3 h-3 text-indigo-600" />,
        };
      default:
        return {
          label: action,
          bg: "bg-slate-100 text-slate-800 border-slate-200",
          icon: <Clock className="w-3 h-3 text-slate-600" />,
        };
    }
  };

  return (
    <div className="clinical-card rounded-2xl p-6 shadow-sm space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-200/80">
        <div className="flex items-center space-x-2">
          <History className="w-5 h-5 text-indigo-600" />
          <h2 className="text-lg font-bold text-slate-900">
            Immutable Audit Trail
          </h2>
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200 font-mono">
            {events.length} records
          </span>
        </div>
        <span className="text-xs text-slate-500 font-mono hidden sm:inline">
          Append-Only Event Ledger
        </span>
      </div>

      {/* Events List */}
      {loading && events.length === 0 ? (
        <div className="py-8 text-center text-slate-400 animate-pulse text-sm">
          Loading audit trail from backend...
        </div>
      ) : events.length === 0 ? (
        <div className="py-8 text-center text-slate-500 bg-slate-50 rounded-xl border border-dashed border-slate-200 text-sm">
          No audit events recorded yet.
        </div>
      ) : (
        <div className="space-y-2.5 max-h-96 overflow-y-auto pr-1">
          {events.map((event) => {
            const badge = getActionBadge(event.action);
            const isOpen = expandedEventId === event.id;

            return (
              <div
                key={event.id}
                className="bg-white border border-slate-200 rounded-xl p-3 hover:border-slate-300 transition-all text-xs space-y-2 shadow-2xs"
              >
                {/* Event Top Bar */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center space-x-2">
                    <span
                      className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-md font-semibold text-[10px] border ${badge.bg}`}
                    >
                      {badge.icon}
                      <span>{badge.label}</span>
                    </span>
                    <span className="font-mono text-slate-400 text-[11px]">
                      {event.entity_type}::{event.entity_id}
                    </span>
                  </div>

                  <div className="flex items-center space-x-1.5 text-slate-400 font-mono text-[10px]">
                    <Clock className="w-3 h-3" />
                    <span>
                      {new Date(event.timestamp).toLocaleString([], {
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                        second: "2-digit",
                      })}
                    </span>
                  </div>
                </div>

                {/* Actor Info */}
                <div className="flex items-center justify-between text-slate-600 pt-0.5">
                  <div className="flex items-center space-x-1 text-slate-500 text-[11px]">
                    <User className="w-3 h-3 text-slate-400" />
                    <span>Actor:</span>
                    <strong className="text-slate-700">{event.performed_by}</strong>
                  </div>

                  <button
                    onClick={() => setExpandedEventId(isOpen ? null : event.id)}
                    className="text-indigo-600 hover:text-indigo-800 text-[11px] font-medium flex items-center space-x-0.5"
                  >
                    <span>{isOpen ? "Hide Details" : "View Payload"}</span>
                    {isOpen ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                  </button>
                </div>

                {/* Collapsible Details */}
                {isOpen && (
                  <div className="p-2.5 bg-slate-900 rounded-lg text-slate-200 font-mono text-[10px] overflow-x-auto space-y-1 border border-slate-800">
                    <div className="text-slate-400">Structured Audit Metadata:</div>
                    <pre className="text-emerald-400">
                      {JSON.stringify(event.details, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
