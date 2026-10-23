"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  approveProposal,
  fetchAuditEvents,
  fetchHealth,
  fetchPatientContext,
  fetchProposals,
  fetchTasks,
  rejectProposal,
  sendAgentMessage,
} from "@/lib/api";
import {
  AuditEvent,
  ChatMessage,
  FollowUpTask,
  HealthStatus,
  PatientContextResponse,
  TaskProposal,
} from "@/lib/types";
import { HeaderBanner } from "@/components/HeaderBanner";
import { PatientContextPanel } from "@/components/PatientContextPanel";
import { FollowUpBoard } from "@/components/FollowUpBoard";
import { ApprovalPanel } from "@/components/ApprovalPanel";
import { ConversationPanel } from "@/components/ConversationPanel";
import { AuditTrail } from "@/components/AuditTrail";
import { AlertCircle, ShieldAlert } from "lucide-react";

export default function SimulatorPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [context, setContext] = useState<PatientContextResponse | null>(null);
  const [tasks, setTasks] = useState<FollowUpTask[]>([]);
  const [proposals, setProposals] = useState<TaskProposal[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [chatLoading, setChatLoading] = useState<boolean>(false);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  // Initial conversational greeting simulating Alexa+ session launch
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "initial-alexa-greeting",
      sender: "alexa",
      text: "CareSync Voice Assistant online. I am connected to the Streamable HTTP MCP server for Eleanor Vance [SYNTHETIC]. How can I assist with post-discharge follow-ups today?",
      timestamp: new Date().toISOString(),
    },
  ]);

  // Load all live backend data concurrently
  const refreshAllData = useCallback(async () => {
    try {
      setLoading(true);
      setErrorBanner(null);

      const [healthData, ctxData, tasksData, propsData, auditData] =
        await Promise.all([
          fetchHealth().catch((e) => {
            console.error("Health fetch failed:", e);
            return null;
          }),
          fetchPatientContext("patient-synthetic-001").catch((e) => {
            console.error("Context fetch failed:", e);
            return null;
          }),
          fetchTasks("patient-synthetic-001").catch((e) => {
            console.error("Tasks fetch failed:", e);
            return [];
          }),
          fetchProposals("patient-synthetic-001").catch((e) => {
            console.error("Proposals fetch failed:", e);
            return [];
          }),
          fetchAuditEvents("patient-synthetic-001").catch((e) => {
            console.error("Audit fetch failed:", e);
            return [];
          }),
        ]);

      setHealth(healthData);
      setContext(ctxData);
      setTasks(tasksData);
      setProposals(propsData);
      setAuditEvents(auditData);

      if (!healthData) {
        setErrorBanner(
          "Cannot connect to CareSync backend at http://127.0.0.1:8000. Ensure the FastAPI and MCP server are running."
        );
      }
    } catch (err: any) {
      setErrorBanner(err.message || "An unexpected error occurred while fetching live data.");
    } finally {
      setLoading(false);
    }
  }, []);

  // HCI: Guarantee that page refresh always loads from the very top hero view
  useEffect(() => {
    if (typeof window !== "undefined") {
      if ("scrollRestoration" in window.history) {
        window.history.scrollRestoration = "manual";
      }
      window.scrollTo({ top: 0, left: 0, behavior: "instant" });
    }
  }, []);

  useEffect(() => {
    refreshAllData();
  }, [refreshAllData]);

  // Handle User Conversational Message Turn
  const handleSendMessage = async (userPrompt: string) => {
    const userMsgId = `user-${Date.now()}`;
    const userMsg: ChatMessage = {
      id: userMsgId,
      sender: "user",
      text: userPrompt,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setChatLoading(true);

    try {
      const turnResult = await sendAgentMessage(userPrompt, "patient-synthetic-001");

      const alexaMsg: ChatMessage = {
        id: `alexa-${Date.now()}`,
        sender: "alexa",
        text: turnResult.response_text,
        timestamp: new Date().toISOString(),
        toolCalls: turnResult.tool_calls,
        pendingProposal: turnResult.pending_proposal,
        safetyRefusal: turnResult.safety_refusal,
      };

      setMessages((prev) => [...prev, alexaMsg]);

      // Refresh tasks, proposals, and audit trail to synchronize UI state with backend
      const [updatedTasks, updatedProps, updatedAudit] = await Promise.all([
        fetchTasks("patient-synthetic-001"),
        fetchProposals("patient-synthetic-001"),
        fetchAuditEvents("patient-synthetic-001"),
      ]);

      setTasks(updatedTasks);
      setProposals(updatedProps);
      setAuditEvents(updatedAudit);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `error-${Date.now()}`,
        sender: "alexa",
        text: `Error processing request: ${err.message || "Backend communication error"}. Ensure FastAPI backend is running.`,
        timestamp: new Date().toISOString(),
        safetyRefusal: false,
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setChatLoading(false);
    }
  };

  // Handle Explicit Human Approval of Staged Proposal
  const handleApproveProposal = async (proposalId: string) => {
    try {
      const confirmedTask = await approveProposal(
        proposalId,
        "Care Coordinator Alex"
      );

      // System notification in chat
      setMessages((prev) => [
        ...prev,
        {
          id: `sys-${Date.now()}`,
          sender: "alexa",
          text: `Proposal ${proposalId} has been explicitly APPROVED by Care Coordinator Alex. New follow-up task "${confirmedTask.title}" (ID: ${confirmedTask.id}) is now active on the follow-up board. Simulated voice reminder scheduled.`,
          timestamp: new Date().toISOString(),
        },
      ]);

      // Synchronize live tables
      const [updatedTasks, updatedProps, updatedAudit] = await Promise.all([
        fetchTasks("patient-synthetic-001"),
        fetchProposals("patient-synthetic-001"),
        fetchAuditEvents("patient-synthetic-001"),
      ]);

      setTasks(updatedTasks);
      setProposals(updatedProps);
      setAuditEvents(updatedAudit);
    } catch (err: any) {
      alert(`Approval error: ${err.message}`);
    }
  };

  // Handle Dismissal / Rejection of Staged Proposal
  const handleRejectProposal = async (proposalId: string) => {
    try {
      await rejectProposal(
        proposalId,
        "Care Coordinator Alex",
        "Dismissed in simulator UI"
      );

      setMessages((prev) => [
        ...prev,
        {
          id: `sys-${Date.now()}`,
          sender: "alexa",
          text: `Proposal ${proposalId} has been dismissed by Care Coordinator Alex. It was NOT added to the follow-up board. Rejection logged in the audit trail.`,
          timestamp: new Date().toISOString(),
        },
      ]);

      const [updatedProps, updatedAudit] = await Promise.all([
        fetchProposals("patient-synthetic-001"),
        fetchAuditEvents("patient-synthetic-001"),
      ]);

      setProposals(updatedProps);
      setAuditEvents(updatedAudit);
    } catch (err: any) {
      alert(`Dismissal error: ${err.message}`);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-100/70">
      {/* 1. Header & Live Connection Status */}
      <HeaderBanner
        health={health}
        loading={loading}
        onRefresh={refreshAllData}
      />

      {/* Backend Error Callout if disconnected */}
      {errorBanner && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-4 w-full">
          <div className="bg-rose-50 border border-rose-300 rounded-xl p-4 flex items-center space-x-3 text-rose-900 text-xs">
            <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
            <div className="flex-1">
              <span className="font-bold">Backend Connection Notice:</span> {errorBanner}
            </div>
            <button
              onClick={refreshAllData}
              className="px-3 py-1 bg-rose-600 text-white rounded-lg font-semibold hover:bg-rose-700 text-xs"
            >
              Retry Connection
            </button>
          </div>
        </div>
      )}

      {/* Main Workspace Layout */}
      <main className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8 flex-1 w-full">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left / Center Work Area: 7 Columns */}
          <div className="lg:col-span-7 space-y-6">
            {/* Patient Context & Ground Truth Excerpts */}
            <PatientContextPanel
              patient={context?.patient || null}
              dischargePlan={context?.discharge_plan || null}
              loading={loading}
            />

            {/* Approval Panel (Staging area for proposals) */}
            <ApprovalPanel
              proposals={proposals}
              onApprove={handleApproveProposal}
              onReject={handleRejectProposal}
              loading={loading}
            />

            {/* Active Follow-Up Tasks Checklist */}
            <FollowUpBoard tasks={tasks} loading={loading} />

            {/* Immutable Audit Trail */}
            <AuditTrail events={auditEvents} loading={loading} />
          </div>

          {/* Right Column: 5 Columns (Sticky Conversational Alexa+ Simulator) */}
          <div className="lg:col-span-5 lg:sticky lg:top-24 space-y-4">
            <ConversationPanel
              messages={messages}
              onSendMessage={handleSendMessage}
              loading={chatLoading}
            />

            {/* Safety & Architecture Footer Callout */}
            <div className="p-4 rounded-xl bg-white border border-slate-200/90 text-[11px] text-slate-500 space-y-1.5 shadow-2xs">
              <div className="flex items-center space-x-1.5 text-slate-700 font-bold">
                <ShieldAlert className="w-3.5 h-3.5 text-indigo-600" />
                <span>CareSync Architectural Invariants</span>
              </div>
              <ul className="list-disc list-inside space-y-0.5 text-slate-600">
                <li>Zero client-side mock data; all state loaded via FastAPI.</li>
                <li>MCP tools invoked over Streamable HTTP (FastMCP spec 2026-07-28).</li>
                <li>Explicit human approval gating prevents autonomous task creation.</li>
                <li>Missing data is kept as <code className="font-mono text-indigo-600">null</code>, never hallucinated.</li>
              </ul>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
