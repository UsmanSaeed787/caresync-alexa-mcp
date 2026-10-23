"use client";

import React, { useState } from "react";
import {
  AlertCircle,
  Bell,
  Calendar,
  CheckCircle,
  Clock,
  FileCheck2,
  Filter,
  ListTodo,
  Quote,
  User,
} from "lucide-react";
import { FollowUpTask } from "@/lib/types";

interface FollowUpBoardProps {
  tasks: FollowUpTask[];
  loading: boolean;
}

export const FollowUpBoard: React.FC<FollowUpBoardProps> = ({ tasks, loading }) => {
  const [filter, setFilter] = useState<"ALL" | "PENDING" | "COMPLETED">("ALL");
  const [expandedSourceId, setExpandedSourceId] = useState<string | null>(null);

  const filteredTasks = tasks.filter((t) => {
    if (filter === "ALL") return true;
    return t.status === filter;
  });

  return (
    <div className="clinical-card rounded-2xl p-6 shadow-sm space-y-4">
      {/* Header and Filter Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-200/80 gap-3">
        <div className="flex items-center space-x-2">
          <ListTodo className="w-5 h-5 text-indigo-600" />
          <h2 className="text-lg font-bold text-slate-900">
            Active Follow-Up Board
          </h2>
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200 font-mono">
            {tasks.length} total
          </span>
        </div>

        {/* Filters */}
        <div className="flex items-center space-x-1.5 bg-slate-100/90 p-1 rounded-xl text-xs font-medium text-slate-600">
          <button
            onClick={() => setFilter("ALL")}
            className={`px-3 py-1 rounded-lg transition-all ${
              filter === "ALL"
                ? "bg-white text-indigo-600 shadow-xs font-semibold"
                : "hover:text-slate-900"
            }`}
          >
            All ({tasks.length})
          </button>
          <button
            onClick={() => setFilter("PENDING")}
            className={`px-3 py-1 rounded-lg transition-all ${
              filter === "PENDING"
                ? "bg-white text-amber-700 shadow-xs font-semibold"
                : "hover:text-slate-900"
            }`}
          >
            Pending ({tasks.filter((t) => t.status === "PENDING").length})
          </button>
          <button
            onClick={() => setFilter("COMPLETED")}
            className={`px-3 py-1 rounded-lg transition-all ${
              filter === "COMPLETED"
                ? "bg-white text-emerald-700 shadow-xs font-semibold"
                : "hover:text-slate-900"
            }`}
          >
            Completed ({tasks.filter((t) => t.status === "COMPLETED").length})
          </button>
        </div>
      </div>

      {/* Task List */}
      {loading && tasks.length === 0 ? (
        <div className="py-12 text-center text-slate-400 animate-pulse text-sm">
          Loading follow-up tasks from backend...
        </div>
      ) : filteredTasks.length === 0 ? (
        <div className="py-12 text-center text-slate-500 bg-slate-50 rounded-xl border border-dashed border-slate-200 text-sm">
          <p>No follow-up tasks found for filter: {filter.toLowerCase()}.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredTasks.map((task) => {
            const isPending = task.status === "PENDING";
            const isCompleted = task.status === "COMPLETED";
            const isSourceOpen = expandedSourceId === task.id;

            return (
              <div
                key={task.id}
                className="bg-white border border-slate-200/90 rounded-xl p-4 hover:border-slate-300 transition-all shadow-xs space-y-3"
              >
                {/* Top Row: Title & Status */}
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="font-semibold text-slate-900 text-sm">
                        {task.title}
                      </span>
                      {task.requires_human_confirmation && (
                        <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-50 text-amber-800 border border-amber-200">
                          <AlertCircle className="w-3 h-3 text-amber-600 mr-0.5" />
                          Review Required
                        </span>
                      )}
                    </div>
                    <span className="text-[11px] font-mono text-slate-400">
                      ID: {task.id}
                    </span>
                  </div>

                  <span
                    className={`inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                      isCompleted
                        ? "clinical-badge-completed"
                        : isPending
                        ? "clinical-badge-pending"
                        : "bg-slate-100 text-slate-700"
                    }`}
                  >
                    {isCompleted ? (
                      <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
                    ) : (
                      <Clock className="w-3.5 h-3.5 text-amber-600" />
                    )}
                    <span>{task.status}</span>
                  </span>
                </div>

                {/* Metadata Row: Due Date & Owner */}
                <div className="flex flex-wrap items-center gap-2 pt-1 text-xs">
                  {/* Due Date */}
                  <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-slate-50 border border-slate-200/70 text-slate-700">
                    <Calendar className="w-3.5 h-3.5 text-slate-500" />
                    <span className="text-slate-500">Due:</span>
                    {task.due_date ? (
                      <span className="font-medium text-slate-900 font-mono">
                        {task.due_date}
                      </span>
                    ) : (
                      <span className="font-semibold text-amber-700 bg-amber-100/70 px-1.5 py-0.5 rounded text-[11px]">
                        Unset (Missing)
                      </span>
                    )}
                  </div>

                  {/* Owner */}
                  <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-slate-50 border border-slate-200/70 text-slate-700">
                    <User className="w-3.5 h-3.5 text-slate-500" />
                    <span className="text-slate-500">Owner:</span>
                    {task.owner ? (
                      <span className="font-medium text-slate-900">
                        {task.owner}
                      </span>
                    ) : (
                      <span className="font-semibold text-amber-700 bg-amber-100/70 px-1.5 py-0.5 rounded text-[11px]">
                        Unassigned (Missing)
                      </span>
                    )}
                  </div>

                  {/* Simulated Reminder Status */}
                  <div className="flex items-center space-x-1 px-2 py-1 rounded-lg bg-indigo-50/60 border border-indigo-100 text-[11px] text-indigo-700 ml-auto">
                    <Bell className="w-3 h-3 text-indigo-500" />
                    <span>Simulated Alexa Reminder</span>
                  </div>
                </div>

                {/* Verbatim Source Evidence Drawer */}
                <div className="pt-2 border-t border-slate-100">
                  <button
                    onClick={() => setExpandedSourceId(isSourceOpen ? null : task.id)}
                    className="text-xs text-indigo-600 hover:text-indigo-800 font-medium flex items-center space-x-1"
                  >
                    <Quote className="w-3 h-3" />
                    <span>{isSourceOpen ? "Hide Source Evidence" : "View Discharge Evidence Quote"}</span>
                  </button>

                  {isSourceOpen && (
                    <div className="mt-2 p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs space-y-1">
                      <div className="flex items-center space-x-1 text-slate-500 font-semibold text-[10px] uppercase">
                        <FileCheck2 className="w-3.5 h-3.5 text-emerald-600" />
                        <span>Verbatim Discharge Reference:</span>
                      </div>
                      <p className="italic text-slate-700 text-xs">
                        "{task.source_reference}"
                      </p>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
