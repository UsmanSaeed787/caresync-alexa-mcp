"use client";

import React, { useState } from "react";
import {
  AlertCircle,
  Calendar,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  FileText,
  HelpCircle,
  Quote,
  User,
} from "lucide-react";
import { Patient, DischargePlan } from "@/lib/types";

interface PatientContextPanelProps {
  patient: Patient | null;
  dischargePlan: DischargePlan | null;
  loading: boolean;
}

export const PatientContextPanel: React.FC<PatientContextPanelProps> = ({
  patient,
  dischargePlan,
  loading,
}) => {
  const [showFullPlan, setShowFullPlan] = useState(false);
  const [expandedExcerpt, setExpandedExcerpt] = useState<number | null>(null);

  if (loading && !patient) {
    return (
      <div className="clinical-card rounded-2xl p-6 animate-pulse">
        <div className="h-6 bg-slate-200 rounded w-1/3 mb-4"></div>
        <div className="h-4 bg-slate-200 rounded w-2/3 mb-2"></div>
        <div className="h-4 bg-slate-200 rounded w-1/2"></div>
      </div>
    );
  }

  if (!patient || !dischargePlan) {
    return (
      <div className="clinical-card rounded-2xl p-6 text-center text-slate-500">
        <p>No patient context loaded.</p>
      </div>
    );
  }

  return (
    <div className="clinical-card rounded-2xl p-6 shadow-sm space-y-5">
      {/* Patient Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-200/80 gap-3">
        <div className="flex items-center space-x-3.5">
          <div className="w-12 h-12 rounded-full bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-600 font-bold text-lg">
            EV
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-lg font-bold text-slate-900">
                {patient.full_name}
              </h2>
              <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
                SYNTHETIC
              </span>
            </div>
            <div className="flex items-center space-x-3 text-xs text-slate-500 mt-0.5 font-mono">
              <span>MRN: <strong className="text-slate-700">{patient.mrn}</strong></span>
              <span>•</span>
              <span>DOB: <strong className="text-slate-700">{patient.date_of_birth}</strong></span>
              <span>•</span>
              <span>ID: <strong className="text-slate-700">{patient.id}</strong></span>
            </div>
          </div>
        </div>

        {/* Admission / Discharge Dates */}
        <div className="flex items-center space-x-2 bg-slate-50 px-3.5 py-2 rounded-xl border border-slate-200/70 text-xs">
          <Calendar className="w-4 h-4 text-indigo-500 shrink-0" />
          <div className="flex flex-col">
            <span className="text-[10px] uppercase font-semibold text-slate-400 tracking-wider">
              Hospital Stay
            </span>
            <span className="font-medium text-slate-700">
              {dischargePlan.admission_date} → {dischargePlan.discharge_date}
            </span>
          </div>
        </div>
      </div>

      {/* Discharge Summary */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center space-x-1.5">
            <FileText className="w-3.5 h-3.5 text-slate-400" />
            <span>Discharge Plan Overview</span>
          </span>
          <button
            onClick={() => setShowFullPlan(!showFullPlan)}
            className="text-xs text-indigo-600 hover:text-indigo-800 font-medium flex items-center space-x-1"
          >
            <span>{showFullPlan ? "Hide Verbatim Text" : "View Full Discharge Text"}</span>
            {showFullPlan ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>
        <p className="text-sm text-slate-700 leading-relaxed bg-slate-50/60 p-3.5 rounded-xl border border-slate-200/60">
          {dischargePlan.summary}
        </p>
      </div>

      {/* Full Discharge Text Drawer */}
      {showFullPlan && (
        <div className="bg-slate-900 text-slate-100 p-4 rounded-xl text-xs font-mono leading-relaxed max-h-60 overflow-y-auto space-y-2 border border-slate-800 shadow-inner">
          <div className="flex items-center justify-between text-slate-400 border-b border-slate-800 pb-2">
            <span className="font-semibold text-slate-300">Synthetic Hospital Discharge Record</span>
            <span className="text-[10px] bg-slate-800 px-2 py-0.5 rounded">Read-Only Ground Truth</span>
          </div>
          <pre className="whitespace-pre-wrap font-sans text-xs text-slate-200 leading-relaxed pt-1">
            {dischargePlan.source_text}
          </pre>
        </div>
      )}

      {/* Explicit Missing Fields Warning (Truthfulness Invariant) */}
      {dischargePlan.explicit_missing_fields && dischargePlan.explicit_missing_fields.length > 0 && (
        <div className="bg-amber-50/80 border border-amber-200/90 rounded-xl p-3.5 text-xs text-amber-900 space-y-2">
          <div className="flex items-center space-x-2 font-semibold">
            <HelpCircle className="w-4 h-4 text-amber-600 shrink-0" />
            <span>Explicitly Missing Discharge Information (Marked Null / Human Review Required):</span>
          </div>
          <div className="flex flex-wrap gap-2 pl-6">
            {dischargePlan.explicit_missing_fields.map((field, idx) => (
              <span
                key={idx}
                className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-md bg-white border border-amber-300 font-mono text-[11px] text-amber-950 font-medium"
              >
                <AlertCircle className="w-3 h-3 text-amber-600 mr-1" />
                {field}
              </span>
            ))}
          </div>
          <p className="text-[11px] text-amber-800 pl-6 italic">
            Per CareSync specification, missing owners and dates are left as null and flagged for coordinator review rather than hallucinated.
          </p>
        </div>
      )}

      {/* Verified Ground Truth Excerpts Accordion */}
      {dischargePlan.source_excerpts && dischargePlan.source_excerpts.length > 0 && (
        <div className="space-y-2">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center space-x-1.5">
            <Quote className="w-3.5 h-3.5 text-slate-400" />
            <span>Verbatim Source Evidence Bank ({dischargePlan.source_excerpts.length} Verified Excerpts)</span>
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
            {dischargePlan.source_excerpts.map((item, idx) => {
              const isOpen = expandedExcerpt === idx;
              const title = item.category || item.label || `Excerpt #${idx + 1}`;
              const content = item.text || item.excerpt || "";
              return (
                <div
                  key={idx}
                  onClick={() => setExpandedExcerpt(isOpen ? null : idx)}
                  className="p-3 bg-white border border-slate-200 rounded-xl hover:border-indigo-300 cursor-pointer transition-all shadow-xs"
                >
                  <div className="flex items-center justify-between font-semibold text-slate-800 mb-1">
                    <span className="flex items-center space-x-1">
                      <CheckCircle2 className="w-3.5 h-3.5 text-indigo-500" />
                      <span>{title}</span>
                    </span>
                    <span className="text-[10px] text-indigo-600 font-medium">
                      {isOpen ? "Collapse" : "Read"}
                    </span>
                  </div>
                  <p className={`text-slate-600 italic text-[11px] ${isOpen ? "" : "line-clamp-2"}`}>
                    "{content}"
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
