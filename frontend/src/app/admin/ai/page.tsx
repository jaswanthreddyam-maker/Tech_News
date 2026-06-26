/* eslint-disable @typescript-eslint/no-unused-vars, react-hooks/exhaustive-deps */
"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { apiFetch } from "../../../services/api";
import { Cpu, CircleDollarSign, RefreshCw, AlertCircle } from "lucide-react";

import { getAiJobs, getAiCosts, testAiPrompt, AIJob, CostAggregation } from "../../../services/api/admin";

export default function AdminAIPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const activeTab = searchParams.get("tab") === "costs" ? "costs" : searchParams.get("tab") === "test" ? "test" : "queue";

  const [jobs, setJobs] = useState<AIJob[]>([]);
  const [costs, setCosts] = useState<CostAggregation | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Prompt tester state
  const [testPromptVersion, setTestPromptVersion] = useState("summary_v2");
  const [testModel, setTestModel] = useState("gpt-4o-mini");
  const [testText, setTestText] = useState("");
  const [testResult, setTestResult] = useState<any>(null);
  const [testing, setTesting] = useState(false);

  const handleTestPrompt = async () => {
    if (!testText.trim()) return;
    setTesting(true);
    setTestResult(null);
    try {
      const res = await testAiPrompt({
        prompt_version: testPromptVersion,
        model: testModel,
        text: testText
      });
      setTestResult(res);
    } catch (err: any) {
      setTestResult({ status: "error", message: err.message });
    } finally {
      setTesting(false);
    }
  };

  const fetchAIOps = async (isSilent = false) => {
    if (activeTab === "test") {
      setLoading(false);
      setRefreshing(false);
      return;
    }
    if (!isSilent) setLoading(true);
    else setRefreshing(true);
    try {
      if (activeTab === "queue") {
        const data = await getAiJobs();
        setJobs(data);
      } else if (activeTab === "costs") {
        const data = await getAiCosts();
        setCosts(data);
      }
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to load AI Operations stats.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchAIOps();
  }, [activeTab]);

  const switchTab = (tabName: "queue" | "costs" | "test") => {
    router.push(`/admin/ai?tab=${tabName}`);
  };

  if (loading) {
    return (
      <div className="space-y-4 font-mono text-[11px]">
        <div className="flex gap-2 border-b border-[#1a1a1a] pb-2">
          <div className="h-6 w-24 bg-neutral-900 animate-pulse" />
          <div className="h-6 w-24 bg-neutral-900 animate-pulse" />
        </div>
        <div className="border border-[#1a1a1a] bg-black p-4 h-64 animate-pulse" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Tabs / Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#1a1a1a] pb-1">
        <div className="flex gap-1.5 font-mono text-[10px]">
          <button
            onClick={() => switchTab("queue")}
            className={`px-3 py-1.5 border border-b-0 border-[#1a1a1a] uppercase font-bold tracking-wider transition-colors ${
              activeTab === "queue"
                ? "bg-[#0c0c0c] text-white border-b-2 border-b-white"
                : "text-[#555] hover:text-[#ccc]"
            }`}
          >
            AI Ingestion Queue
          </button>
          <button
            onClick={() => switchTab("costs")}
            className={`px-3 py-1.5 border border-b-0 border-[#1a1a1a] uppercase font-bold tracking-wider transition-colors ${
              activeTab === "costs"
                ? "bg-[#0c0c0c] text-white border-b-2 border-b-white"
                : "text-[#555] hover:text-[#ccc]"
            }`}
          >
            Cost Analytics
          </button>
          <button
            onClick={() => switchTab("test")}
            className={`px-3 py-1.5 border border-b-0 border-[#1a1a1a] uppercase font-bold tracking-wider transition-colors ${
              activeTab === "test"
                ? "bg-[#0c0c0c] text-white border-b-2 border-b-white"
                : "text-[#555] hover:text-[#ccc]"
            }`}
          >
            Prompt Tester
          </button>
        </div>
        <button
          onClick={() => fetchAIOps(true)}
          disabled={refreshing}
          className="flex items-center gap-1.5 font-mono text-[9px] tracking-widest uppercase text-[#888] hover:text-white transition-colors disabled:opacity-50 self-end sm:self-center"
        >
          <RefreshCw className={`w-3 h-3 ${refreshing ? "animate-spin" : ""}`} />
          REFRESH
        </button>
      </div>

      {error && (
        <div className="border border-red-500/30 bg-red-500/5 px-3 py-2 flex items-center gap-2">
          <AlertCircle className="w-3.5 h-3.5 text-red-400 shrink-0" />
          <p className="font-mono text-[10px] text-red-400">{error}</p>
        </div>
      )}

      {/* Main Content */}
      {activeTab === "queue" ? (
        <div className="border border-[#1a1a1a] bg-black overflow-x-auto">
          <table className="w-full text-left font-mono text-[11px]">
            <thead>
              <tr className="border-b border-[#1a1a1a] bg-[#0c0c0c] text-[#555] select-none text-[9px]">
                <th className="p-3">JOB ID</th>
                <th className="p-3">ARTICLE ID</th>
                <th className="p-3">PROVIDER</th>
                <th className="p-3">MODEL</th>
                <th className="p-3">TOKENS (P/C)</th>
                <th className="p-3">COST</th>
                <th className="p-3">STATUS</th>
                <th className="p-3 text-right">COMPLETED</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#111]">
              {jobs.map((j) => (
                <tr key={j.id} className="hover:bg-[#060606] transition-colors">
                  <td className="p-3 text-[#555]">{j.id}</td>
                  <td className="p-3 text-[#ccc]">{j.raw_article_id}</td>
                  <td className="p-3 text-[#888] uppercase">{j.provider}</td>
                  <td className="p-3 text-[#888]">{j.model_name}</td>
                  <td className="p-3 text-[#ccc]">
                    {j.tokens_prompt} / {j.tokens_completion}
                  </td>
                  <td className="p-3 text-emerald-400">${j.cost_usd.toFixed(5)}</td>
                  <td className="p-3">
                    <span
                      className={`inline-flex items-center px-1.5 py-0.5 text-[8px] font-bold tracking-wider uppercase border ${
                        j.status === "completed"
                          ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-400"
                          : j.status === "failed"
                          ? "border-red-500/20 bg-red-500/5 text-red-400"
                          : "border-blue-500/20 bg-blue-500/5 text-blue-400 animate-pulse"
                      }`}
                    >
                      {j.status}
                    </span>
                  </td>
                  <td className="p-3 text-right text-[#555]">
                    {j.completed_at ? new Date(j.completed_at).toLocaleTimeString() : "-"}
                  </td>
                </tr>
              ))}
              {jobs.length === 0 && (
                <tr>
                  <td colSpan={8} className="p-8 text-center text-[#555]">
                    No AI jobs processed in queue yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      ) : activeTab === "costs" ? (
        costs && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Aggregate summary */}
            <div className="border border-[#1a1a1a] bg-[#0c0c0c] p-4 col-span-1 space-y-4">
              <h3 className="font-mono text-[9px] tracking-widest uppercase text-[#888] font-bold">
                FINANCIAL SUMMARY
              </h3>
              <div className="border border-[#1a1a1a] bg-black p-3.5">
                <p className="font-mono text-[8px] text-[#555] tracking-wider uppercase mb-1">
                  Total System Cost
                </p>
                <p className="font-mono text-3xl font-bold text-emerald-400">
                  ${costs.aggregated.total_cost_usd.toFixed(4)}
                </p>
              </div>
              <div className="grid grid-cols-2 gap-2 font-mono text-[10px]">
                <div className="border border-[#1a1a1a] bg-black p-2">
                  <p className="text-[#555] text-[7px] uppercase tracking-wider mb-1">
                    Prompt Tokens
                  </p>
                  <p className="text-[#ccc] font-bold">{costs.aggregated.prompt_tokens}</p>
                </div>
                <div className="border border-[#1a1a1a] bg-black p-2">
                  <p className="text-[#555] text-[7px] uppercase tracking-wider mb-1">
                    Completion Tokens
                  </p>
                  <p className="text-[#ccc] font-bold">{costs.aggregated.completion_tokens}</p>
                </div>
              </div>
            </div>

            {/* Model Breakdown */}
            <div className="border border-[#1a1a1a] bg-black p-4 col-span-2 overflow-x-auto">
              <h3 className="font-mono text-[9px] tracking-widest uppercase text-[#888] font-bold mb-3">
                EXPENSES BY MODEL TYPE
              </h3>
              <table className="w-full text-left font-mono text-[11px]">
                <thead>
                  <tr className="border-b border-[#1a1a1a] text-[#555] select-none text-[8px]">
                    <th className="pb-2">MODEL IDENTIFIER</th>
                    <th className="pb-2 text-right">TOTAL EXPENSES</th>
                    <th className="pb-2 text-right">TOTAL INGESTED JOBS</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#111]">
                  {costs.models_breakdown.map((m) => (
                    <tr key={m.model}>
                      <td className="py-2.5 text-[#ccc] font-semibold">{m.model}</td>
                      <td className="py-2.5 text-right text-emerald-400 font-bold">
                        ${m.cost.toFixed(4)}
                      </td>
                      <td className="py-2.5 text-right text-[#888]">{m.jobs_count}</td>
                    </tr>
                  ))}
                  {costs.models_breakdown.length === 0 && (
                    <tr>
                      <td colSpan={3} className="py-4 text-center text-[#555]">
                        No metrics registered yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )
      ) : activeTab === "test" ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Prompt Editor */}
          <div className="border border-[#1a1a1a] bg-black p-4 space-y-4">
            <h3 className="font-mono text-[9px] tracking-widest uppercase text-[#888] font-bold">
              PROMPT EDITOR & CONFIG
            </h3>
            <div className="space-y-3">
              <div>
                <label htmlFor="test-prompt-version" className="block text-[10px] text-[#555] uppercase tracking-wider mb-1">
                  Prompt Version
                </label>
                <input
                  id="test-prompt-version"
                  type="text"
                  value={testPromptVersion}
                  onChange={(e) => setTestPromptVersion(e.target.value)}
                  className="w-full bg-[#0c0c0c] border border-[#1a1a1a] text-[#ccc] p-2 text-[11px] font-mono focus:outline-none focus:border-white transition-colors"
                />
              </div>
              <div>
                <label htmlFor="test-model" className="block text-[10px] text-[#555] uppercase tracking-wider mb-1">
                  Target Model
                </label>
                <select
                  id="test-model"
                  value={testModel}
                  onChange={(e) => setTestModel(e.target.value)}
                  className="w-full bg-[#0c0c0c] border border-[#1a1a1a] text-[#ccc] p-2 text-[11px] font-mono focus:outline-none focus:border-white transition-colors"
                >
                  <option value="gpt-4o-mini">GPT-4o Mini</option>
                  <option value="gpt-4o">GPT-4o</option>
                  <option value="claude-3-haiku-20240307">Claude 3 Haiku</option>
                  <option value="claude-3-5-sonnet-20240620">Claude 3.5 Sonnet</option>
                </select>
              </div>
              <div>
                <label htmlFor="test-text" className="block text-[10px] text-[#555] uppercase tracking-wider mb-1">
                  Input Article Content
                </label>
                <textarea
                  id="test-text"
                  value={testText}
                  onChange={(e) => setTestText(e.target.value)}
                  placeholder="Paste raw article content to summarize..."
                  className="w-full bg-[#0c0c0c] border border-[#1a1a1a] text-[#ccc] p-2 h-40 text-[11px] font-mono focus:outline-none focus:border-white transition-colors resize-none"
                />
              </div>
              <button
                onClick={handleTestPrompt}
                disabled={testing || !testText.trim()}
                className="w-full bg-white text-black font-bold uppercase tracking-wider text-[11px] py-2 hover:bg-[#ccc] transition-colors disabled:opacity-50"
              >
                {testing ? "Testing Prompt..." : "Execute Test"}
              </button>
            </div>
          </div>

          {/* Test Results */}
          <div className="border border-[#1a1a1a] bg-black p-4 space-y-4">
            <h3 className="font-mono text-[9px] tracking-widest uppercase text-[#888] font-bold">
              EXECUTION RESULTS
            </h3>
            {testResult ? (
              <div className="space-y-3">
                {testResult.status === "success" ? (
                  <>
                    <div className="grid grid-cols-3 gap-2 font-mono text-[9px] uppercase tracking-wider">
                      <div className="border border-[#1a1a1a] bg-[#0c0c0c] p-2">
                        <p className="text-[#555] mb-1">Tokens (P/C)</p>
                        <p className="text-[#ccc] font-bold">
                          {testResult.raw_response?.usage?.prompt_tokens || 0} /{" "}
                          {testResult.raw_response?.usage?.completion_tokens || 0}
                        </p>
                      </div>
                      <div className="border border-[#1a1a1a] bg-[#0c0c0c] p-2">
                        <p className="text-[#555] mb-1">Latency</p>
                        <p className="text-[#ccc] font-bold">
                          {testResult.raw_response?.latency_ms || 0} ms
                        </p>
                      </div>
                      <div className="border border-emerald-500/20 bg-emerald-500/5 p-2">
                        <p className="text-emerald-500 mb-1">Cache Hit</p>
                        <p className="text-emerald-400 font-bold">
                          {testResult.raw_response?.cache_hit ? "YES" : "NO"}
                        </p>
                      </div>
                    </div>
                    <div>
                      <h4 className="block text-[10px] text-[#555] uppercase tracking-wider mb-1 mt-2">
                        System Prompt
                      </h4>
                      <div className="bg-[#0c0c0c] border border-[#1a1a1a] p-3 max-h-32 overflow-y-auto">
                        <pre className="text-[10px] text-[#888] whitespace-pre-wrap font-mono">
                          {testResult.system_prompt || "-"}
                        </pre>
                      </div>

                      <h4 className="block text-[10px] text-[#555] uppercase tracking-wider mb-1 mt-3">
                        User Prompt
                      </h4>
                      <div className="bg-[#0c0c0c] border border-[#1a1a1a] p-3 max-h-32 overflow-y-auto">
                        <pre className="text-[10px] text-[#888] whitespace-pre-wrap font-mono">
                          {testResult.user_prompt || "-"}
                        </pre>
                      </div>

                      <h4 className="block text-[10px] text-[#555] uppercase tracking-wider mb-1 mt-3">
                        Generated Output Payload
                      </h4>
                      <div className="bg-[#0c0c0c] border border-[#1a1a1a] p-3 max-h-60 overflow-y-auto">
                        <pre className="text-[10px] text-emerald-400 whitespace-pre-wrap font-mono">
                          {JSON.stringify(testResult.raw_response?.payload, null, 2)}
                        </pre>
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="border border-red-500/30 bg-red-500/5 p-3">
                    <p className="text-red-400 text-[11px] font-mono whitespace-pre-wrap">
                      {testResult.message}
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="h-full flex items-center justify-center text-[#555] font-mono text-[11px] italic">
                Awaiting execution...
              </div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
