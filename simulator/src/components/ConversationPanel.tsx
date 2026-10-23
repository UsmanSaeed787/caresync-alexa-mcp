"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  AlertOctagon,
  ArrowRight,
  Bot,
  ChevronDown,
  ChevronUp,
  Cpu,
  Mic,
  Radio,
  Send,
  Sparkles,
  Terminal,
  User,
} from "lucide-react";
import { ChatMessage, ToolCallTrace } from "@/lib/types";

interface ConversationPanelProps {
  messages: ChatMessage[];
  onSendMessage: (text: string) => Promise<void>;
  loading: boolean;
}

const QUICK_PROMPTS = [
  {
    label: "Outstanding Tasks",
    prompt: "What follow-ups are still outstanding for Eleanor Vance?",
    tag: "Golden Path 1",
  },
  {
    label: "Prepare PCP Follow-Up",
    prompt: "Prepare a follow-up task for the primary-care appointment",
    tag: "Golden Path 2",
  },
  {
    label: "Show Audit Trail",
    prompt: "Show recent audit log events for this patient",
    tag: "Auditing",
  },
  {
    label: "Emergency Safety Test",
    prompt: "Patient reports severe crushing chest pain, what medication should I give?",
    tag: "Safety Invariant",
  },
];

export const ConversationPanel: React.FC<ConversationPanelProps> = ({
  messages,
  onSendMessage,
  loading,
}) => {
  const [inputText, setInputText] = useState("");
  const [expandedTools, setExpandedTools] = useState<Record<string, boolean>>({});
  const chatBodyRef = useRef<HTMLDivElement>(null);

  // HCI: Auto-scroll ONLY within the chat box container, NEVER jumping or scrolling the window!
  useEffect(() => {
    if (chatBodyRef.current) {
      chatBodyRef.current.scrollTop = chatBodyRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || loading) return;
    const text = inputText;
    setInputText("");
    await onSendMessage(text);
  };

  const toggleToolExpand = (msgId: string, toolIdx: number) => {
    const key = `${msgId}-${toolIdx}`;
    setExpandedTools((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="clinical-card rounded-2xl shadow-sm flex flex-col h-[470px] max-h-[calc(100vh-160px)] overflow-hidden border border-slate-200 bg-white">
      {/* 1. Header: Compact, Sleek Alexa+ Simulation Indicator */}
      <div className="px-4 py-2.5 border-b border-slate-200 bg-slate-50/90 flex items-center justify-between shrink-0">
        <div className="flex items-center space-x-2.5">
          <div className="w-7 h-7 rounded-full bg-gradient-to-tr from-indigo-600 to-sky-500 flex items-center justify-center text-white shadow-xs">
            <Radio className="w-3.5 h-3.5 animate-pulse" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-slate-900 flex items-center space-x-1.5">
              <span>Alexa+ Care Coordinator Voice Agent</span>
              <span className="text-[9px] px-1.5 py-0.2 rounded-full bg-indigo-100 text-indigo-700 font-semibold uppercase">
                Simulated
              </span>
            </h3>
            <p className="text-[10px] text-slate-500">
              FastMCP Streamable HTTP • Live Tool Tracing
            </p>
          </div>
        </div>
      </div>

      {/* 2. Messages List Area (Takes available height, independently scrollable) */}
      <div
        ref={chatBodyRef}
        className="flex-1 min-h-0 p-3.5 overflow-y-auto space-y-3 bg-gradient-to-b from-slate-50/20 to-white"
      >
        {messages.map((msg) => {
          const isUser = msg.sender === "user";

          return (
            <div
              key={msg.id}
              className={`flex flex-col ${isUser ? "items-end" : "items-start"} space-y-1`}
            >
              <div
                className={`flex items-start space-x-2 max-w-[90%] ${
                  isUser ? "flex-row-reverse space-x-reverse" : "flex-row"
                }`}
              >
                {/* Avatar */}
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 text-xs font-semibold ${
                    isUser
                      ? "bg-slate-700 text-white"
                      : "bg-indigo-600 text-white shadow-xs"
                  }`}
                >
                  {isUser ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
                </div>

                {/* Bubble */}
                <div
                  className={`p-3 rounded-2xl text-xs leading-relaxed ${
                    isUser
                      ? "bg-slate-900 text-white rounded-tr-none shadow-xs"
                      : msg.safetyRefusal
                      ? "bg-rose-50 text-rose-950 border border-rose-200 rounded-tl-none shadow-xs"
                      : "bg-white text-slate-800 border border-slate-200/90 rounded-tl-none shadow-xs"
                  }`}
                >
                  {msg.safetyRefusal && (
                    <div className="flex items-center space-x-1.5 text-rose-700 font-bold mb-1 pb-1 border-b border-rose-200 text-[10px]">
                      <AlertOctagon className="w-3.5 h-3.5 text-rose-600 shrink-0" />
                      <span>SAFETY REFUSAL — EMERGENCY CLINICAL NOTICE</span>
                    </div>
                  )}

                  <p className="whitespace-pre-wrap">{msg.text}</p>

                  <div className="mt-1 text-[9px] text-slate-400 text-right">
                    {new Date(msg.timestamp).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                      second: "2-digit",
                    })}
                  </div>
                </div>
              </div>

              {/* MCP Tool Calling Traces */}
              {msg.toolCalls && msg.toolCalls.length > 0 && (
                <div className="ml-8 max-w-[90%] space-y-1.5 pt-0.5 w-full">
                  <div className="flex items-center space-x-1 text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
                    <Cpu className="w-3 h-3 text-indigo-500" />
                    <span>Real-Time MCP Tool Execution ({msg.toolCalls.length})</span>
                  </div>

                  {msg.toolCalls.map((tool, idx) => {
                    const toolKey = `${msg.id}-${idx}`;
                    const isOpen = expandedTools[toolKey];

                    return (
                      <div
                        key={idx}
                        className="bg-slate-900 text-slate-100 rounded-xl overflow-hidden text-[11px] font-mono border border-slate-800 shadow-xs"
                      >
                        <button
                          onClick={() => toggleToolExpand(msg.id, idx)}
                          className="w-full px-2.5 py-1.5 bg-slate-950/80 hover:bg-slate-950 flex items-center justify-between text-left transition-colors"
                        >
                          <div className="flex items-center space-x-1.5">
                            <Terminal className="w-3 h-3 text-sky-400" />
                            <span className="font-bold text-sky-300">
                              mcp::{tool.tool_name}
                            </span>
                          </div>
                          <div className="flex items-center space-x-1 text-[10px] text-slate-400">
                            <span>{isOpen ? "Collapse" : "Inspect Payload"}</span>
                            {isOpen ? (
                              <ChevronUp className="w-3 h-3" />
                            ) : (
                              <ChevronDown className="w-3 h-3" />
                            )}
                          </div>
                        </button>

                        {isOpen && (
                          <div className="p-2.5 space-y-1.5 bg-slate-900/90 border-t border-slate-800 text-[10px]">
                            <div>
                              <span className="text-slate-400 uppercase font-semibold text-[9px] block">
                                Arguments:
                              </span>
                              <pre className="text-slate-300 bg-slate-950/60 p-1.5 rounded border border-slate-800 overflow-x-auto">
                                {JSON.stringify(tool.arguments, null, 2)}
                              </pre>
                            </div>
                            <div>
                              <span className="text-slate-400 uppercase font-semibold text-[9px] block">
                                Server Payload:
                              </span>
                              <pre className="text-emerald-400 bg-slate-950/60 p-1.5 rounded border border-slate-800 overflow-x-auto max-h-36">
                                {JSON.stringify(tool.result, null, 2)}
                              </pre>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}

        {loading && (
          <div className="flex items-center space-x-2 text-indigo-600 text-xs font-medium py-1.5 ml-8">
            <Radio className="w-3.5 h-3.5 animate-spin text-indigo-600" />
            <span>Alexa+ Agent querying Streamable HTTP MCP tools...</span>
          </div>
        )}
      </div>

      {/* 3. Quick Prompts Scrollable Bar */}
      <div className="px-3 py-1.5 border-t border-slate-200/90 bg-slate-50/80 overflow-x-auto shrink-0 flex items-center space-x-1.5">
        <span className="text-[9px] font-bold uppercase tracking-wider text-slate-400 flex items-center space-x-1 shrink-0">
          <Sparkles className="w-2.5 h-2.5 text-indigo-500" />
          <span>Quick Prompts:</span>
        </span>
        {QUICK_PROMPTS.map((qp, idx) => (
          <button
            key={idx}
            disabled={loading}
            onClick={() => onSendMessage(qp.prompt)}
            className="shrink-0 px-2 py-0.5 rounded-lg bg-white border border-slate-200 hover:border-indigo-400 text-slate-700 hover:text-indigo-700 text-[11px] font-medium transition-all shadow-2xs disabled:opacity-50 flex items-center space-x-1"
          >
            <span>{qp.label}</span>
            <ArrowRight className="w-2.5 h-2.5 text-slate-400" />
          </button>
        ))}
      </div>

      {/* 4. Permanently Anchored Input Field (Always in View!) */}
      <form
        onSubmit={handleSubmit}
        className="p-2.5 border-t border-slate-200 bg-white flex items-center space-x-2 shrink-0"
      >
        <div className="relative flex-1">
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            disabled={loading}
            placeholder="Type or simulate an Alexa+ voice prompt..."
            className="w-full pl-3 pr-8 py-2 rounded-xl border border-slate-200 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/25 focus:border-indigo-500 transition-all shadow-2xs"
          />
          <Mic className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-2.5 pointer-events-none" />
        </div>

        <button
          type="submit"
          disabled={!inputText.trim() || loading}
          className="p-2 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-700 hover:to-indigo-800 text-white shadow-xs transition-all disabled:opacity-40 shrink-0 cursor-pointer active:scale-95"
          title="Send Prompt"
          aria-label="Send Prompt"
        >
          <Send className="w-3.5 h-3.5" />
        </button>
      </form>
    </div>
  );
};
