"use client";

import React, { useState } from "react";
import {
  AlertTriangle,
  Calendar,
  Check,
  FileCheck,
  Lock,
  Quote,
  ShieldAlert,
  UserCheck,
  X,
} from "lucide-react";
import { TaskProposal } from "@/lib/types";

interface ApprovalPanelProps {
  proposals: TaskProposal[];
  onApprove: (proposalId: string) => Promise<void>;
  onReject: (proposalId: string) => Promise<void>;
  loading: boolean;
}

export const ApprovalPanel: React.FC<ApprovalPanelProps> = ({
  proposals,
  onApprove,
  onReject,
  loading,
}) => {
  const [actingId, setActingId] = useState<string | null>(null);

  const pendingProposals = proposals.filter((p) => p.status === "PENDING");

  if (pendingProposals.length === 0) {
    return (
      <div className="clinical-card rounded-2xl p-5 shadow-sm border-dashed border-slate-300">
        <div className="flex items-center space-x-3 text-slate-500">
          <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center text-slate-400">
            <Lock className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-700">
              Approval Staging Area — No Pending Proposals
            </h3>
            <p className="text-xs text-slate-500">
              Ask Alexa+ to "Prepare a follow-up task..." to stage an approval-gated proposal with verbatim evidence.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="clinical-card rounded-2xl p-6 shadow-sm border-2 border-indigo-200/90 bg-gradient-to-b from-indigo-50/40 to-white space-y-4">
      {/* Panel Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-indigo-100 gap-2">
        <div className="flex items-center space-x-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white shadow-sm">
            <ShieldAlert className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-900">
              Pending Human Approval ({pendingProposals.length})
            </h3>
            <p className="text-xs text-indigo-700">
              Approval-gated workflow: Explicit review required before task is activated.
            </p>
          </div>
        </div>
        <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-indigo-100 text-indigo-800 border border-indigo-200">
          Requires Coordinator Signature
        </span>
      </div>

      {/* List of Pending Proposals */}
      <div className="space-y-4 max-h-[440px] overflow-y-auto pr-1">
        {pendingProposals.map((proposal) => {
          const isBusy = actingId === proposal.id || loading;

          return (
            <div
              key={proposal.id}
              className="bg-white rounded-xl border border-indigo-200 p-5 shadow-xs space-y-4 transition-all"
            >
              {/* Proposal Title and ID */}
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
                <div>
                  <span className="text-[10px] font-mono uppercase tracking-wider text-indigo-600 font-bold bg-indigo-50 px-2 py-0.5 rounded">
                    Proposed Follow-Up Task
                  </span>
                  <h4 className="text-base font-bold text-slate-900 mt-1">
                    {proposal.title}
                  </h4>
                  <span className="text-xs font-mono text-slate-400">
                    Proposal ID: {proposal.id} • Proposed by: {proposal.proposed_by}
                  </span>
                </div>

                <div className="flex items-center space-x-2 text-xs">
                  <span className="px-2.5 py-1 rounded-md bg-amber-50 text-amber-800 border border-amber-200 font-semibold">
                    PENDING APPROVAL
                  </span>
                </div>
              </div>

              {/* Source Evidence Quote */}
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs space-y-1">
                <div className="flex items-center space-x-1 text-slate-500 font-semibold text-[10px] uppercase">
                  <Quote className="w-3.5 h-3.5 text-indigo-500" />
                  <span>Ground Truth Discharge Evidence:</span>
                </div>
                <p className="italic text-slate-800">
                  "{proposal.source_reference}"
                </p>
              </div>

              {/* Proposed Fields: Due Date & Owner */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200 flex items-center space-x-2">
                  <Calendar className="w-4 h-4 text-slate-400" />
                  <div>
                    <span className="text-[10px] text-slate-400 uppercase font-semibold block">
                      Target Due Date
                    </span>
                    {proposal.due_date ? (
                      <span className="font-mono font-bold text-slate-800">
                        {proposal.due_date}
                      </span>
                    ) : (
                      <span className="text-amber-800 font-semibold bg-amber-100/70 px-1.5 py-0.5 rounded text-[11px]">
                        Explicitly Unset (Unstated in text)
                      </span>
                    )}
                  </div>
                </div>

                <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200 flex items-center space-x-2">
                  <UserCheck className="w-4 h-4 text-slate-400" />
                  <div>
                    <span className="text-[10px] text-slate-400 uppercase font-semibold block">
                      Target Owner / Assignee
                    </span>
                    {proposal.owner ? (
                      <span className="font-bold text-slate-800">
                        {proposal.owner}
                      </span>
                    ) : (
                      <span className="text-amber-800 font-semibold bg-amber-100/70 px-1.5 py-0.5 rounded text-[11px]">
                        Explicitly Unassigned (Unstated in text)
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Explicit Approval Actions */}
              <div className="pt-3 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-3">
                <p className="text-[11px] text-slate-500">
                  Clicking <strong>Approve & Schedule</strong> will write the task to the database, trigger simulated reminders, and log an immutable audit event.
                </p>

                <div className="flex items-center space-x-2 shrink-0">
                  <button
                    onClick={async () => {
                      setActingId(proposal.id);
                      await onReject(proposal.id);
                      setActingId(null);
                    }}
                    disabled={isBusy}
                    className="px-3.5 py-2 rounded-xl border border-slate-300 text-slate-700 hover:bg-slate-100 font-semibold text-xs flex items-center space-x-1.5 transition-colors disabled:opacity-50"
                  >
                    <X className="w-3.5 h-3.5 text-slate-500" />
                    <span>Dismiss</span>
                  </button>

                  <button
                    onClick={async () => {
                      setActingId(proposal.id);
                      await onApprove(proposal.id);
                      setActingId(null);
                    }}
                    disabled={isBusy}
                    className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs flex items-center space-x-1.5 shadow-md shadow-indigo-500/20 transition-all disabled:opacity-50"
                  >
                    <Check className="w-4 h-4" />
                    <span>{isBusy ? "Approving..." : "Approve & Schedule Task"}</span>
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
