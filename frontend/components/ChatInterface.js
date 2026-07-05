"use client";

import { useState, useRef } from "react";
import CodeEditor from "./CodeEditor";
import MarkdownRenderer from "./MarkdownRenderer";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const LANGUAGES = ["python", "javascript", "java", "cpp"];
const MODELS = [
  { id: "openai/gpt-oss-120b", label: "GPT-OSS 120B (higher quality)" },
  { id: "openai/gpt-oss-20b", label: "GPT-OSS 20B (faster)" },
];

const TABS = ["generate", "review", "debug"];

function ErrorBanner({ error }) {
  if (!error) return null;
  const isRateLimit = error.status === 429;
  return (
    <div
      className={`rounded-lg border p-3 text-sm ${
        isRateLimit
          ? "border-amber-600 bg-amber-950/50 text-amber-300"
          : "border-red-700 bg-red-950/50 text-red-300"
      }`}
    >
      {isRateLimit
        ? "You've hit the rate limit (50 requests/hour). Please wait a bit before trying again."
        : error.message || "Something went wrong. Please try again."}
    </div>
  );
}

function ModelLanguageRow({ language, setLanguage, model, setModel }) {
  return (
    <div className="flex flex-wrap gap-3">
      <select
        value={language}
        onChange={(e) => setLanguage(e.target.value)}
        className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-indigo-500 focus:outline-none"
      >
        {LANGUAGES.map((lang) => (
          <option key={lang} value={lang}>
            {lang}
          </option>
        ))}
      </select>
      <select
        value={model}
        onChange={(e) => setModel(e.target.value)}
        className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 focus:border-indigo-500 focus:outline-none"
      >
        {MODELS.map((m) => (
          <option key={m.id} value={m.id}>
            {m.label}
          </option>
        ))}
      </select>
    </div>
  );
}

async function callApi(path, body) {
  let res;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw { status: 0, message: "Could not reach the backend. Is it running?" };
  }
  if (!res.ok) {
    let detail = "Request failed.";
    try {
      const data = await res.json();
      detail = data.detail || detail;
    } catch {
      // ignore parse errors
    }
    throw { status: res.status, message: detail };
  }
  return res.json();
}

function GenerateTab() {
  const [prompt, setPrompt] = useState("");
  const [language, setLanguage] = useState("python");
  const [model, setModel] = useState(MODELS[0].id);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState("");
  const [error, setError] = useState(null);
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef(null);

  const toggleVoice = () => {
    const SpeechRecognition =
      typeof window !== "undefined" &&
      (window.SpeechRecognition || window.webkitSpeechRecognition);
    if (!SpeechRecognition) {
      setError({ message: "Voice input isn't supported in this browser." });
      return;
    }
    if (listening) {
      recognitionRef.current?.stop();
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      setPrompt((prev) => (prev ? `${prev} ${transcript}` : transcript));
    };
    recognition.onend = () => setListening(false);
    recognition.onerror = () => setListening(false);
    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);
  };

  const submit = async () => {
    setLoading(true);
    setError(null);
    setResult("");
    try {
      const data = await callApi("/agent/generate", { prompt, language, model });
      setResult(data.result);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <ModelLanguageRow
        language={language}
        setLanguage={setLanguage}
        model={model}
        setModel={setModel}
      />
      <div className="relative">
        <CodeEditor
          label="What do you want to build?"
          value={prompt}
          onChange={setPrompt}
          placeholder="e.g. Write a function that merges two sorted lists"
          rows={6}
        />
        <button
          type="button"
          onClick={toggleVoice}
          title="Voice input"
          className={`absolute right-2 top-8 rounded-full p-2 text-sm ${
            listening
              ? "bg-red-600 text-white"
              : "bg-slate-800 text-slate-300 hover:bg-slate-700"
          }`}
        >
          🎤
        </button>
      </div>
      <button
        onClick={submit}
        disabled={loading || !prompt.trim()}
        className="self-start rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {loading ? "Generating..." : "Generate Code"}
      </button>
      <ErrorBanner error={error} />
      {result && (
        <div className="rounded-lg border border-slate-700 bg-slate-900 p-4">
          <MarkdownRenderer content={result} />
        </div>
      )}
    </div>
  );
}

function ReviewTab() {
  const [code, setCode] = useState("");
  const [language, setLanguage] = useState("python");
  const [model, setModel] = useState(MODELS[0].id);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState("");
  const [error, setError] = useState(null);
  const [sessionId, setSessionId] = useState(null);

  const useRagExample = () => {
    setSessionId("demo-session");
    setCode(
      "def get(u):\n    r = requests.get(u)\n    return r.json()\n"
    );
    setLanguage("python");
  };

  const handleFileUpload = async (e) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;
    setUploading(true);
    setError(null);
    try {
      const formData = new FormData();
      files.forEach((f) => formData.append("files", f));
      if (sessionId) formData.append("session_id", sessionId);

      const res = await fetch(`${API_URL}/rag/upload`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw { status: res.status, message: data.detail || "Upload failed." };
      }
      const data = await res.json();
      setSessionId(data.session_id);
    } catch (err) {
      setError(err);
    } finally {
      setUploading(false);
    }
  };

  const submit = async () => {
    setLoading(true);
    setError(null);
    setResult("");
    try {
      const data = await callApi("/agent/review", {
        code,
        language,
        model,
        session_id: sessionId || undefined,
      });
      setResult(data.result);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <ModelLanguageRow
        language={language}
        setLanguage={setLanguage}
        model={model}
        setModel={setModel}
      />
      <CodeEditor
        label="Code to review"
        value={code}
        onChange={setCode}
        placeholder="Paste the code you'd like reviewed..."
        rows={10}
      />
      <div className="flex flex-wrap items-center gap-3">
        <label className="cursor-pointer rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm hover:bg-slate-700">
          {uploading ? "Uploading..." : "Upload files for context"}
          <input
            type="file"
            multiple
            className="hidden"
            onChange={handleFileUpload}
            disabled={uploading}
          />
        </label>
        <button
          type="button"
          onClick={useRagExample}
          className="rounded-lg border border-indigo-600 px-3 py-2 text-sm text-indigo-300 hover:bg-indigo-950"
        >
          Try RAG Example
        </button>
        {sessionId && (
          <span className="rounded-full bg-emerald-950 px-3 py-1 text-xs text-emerald-300">
            session: {sessionId}
          </span>
        )}
      </div>
      <button
        onClick={submit}
        disabled={loading || !code.trim()}
        className="self-start rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {loading ? "Reviewing..." : "Review Code"}
      </button>
      <ErrorBanner error={error} />
      {result && (
        <div className="rounded-lg border border-slate-700 bg-slate-900 p-4">
          <MarkdownRenderer content={result} />
        </div>
      )}
    </div>
  );
}

function DebugTab() {
  const [code, setCode] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [language, setLanguage] = useState("python");
  const [model, setModel] = useState(MODELS[0].id);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState("");
  const [error, setError] = useState(null);

  const submit = async () => {
    setLoading(true);
    setError(null);
    setResult("");
    try {
      const data = await callApi("/agent/debug", {
        code,
        error: errorMsg,
        language,
        model,
      });
      setResult(data.result);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <ModelLanguageRow
        language={language}
        setLanguage={setLanguage}
        model={model}
        setModel={setModel}
      />
      <CodeEditor
        label="Code with the bug"
        value={code}
        onChange={setCode}
        placeholder="Paste the buggy code..."
        rows={8}
      />
      <CodeEditor
        label="Error message"
        value={errorMsg}
        onChange={setErrorMsg}
        placeholder="Paste the error / traceback..."
        rows={4}
      />
      <button
        onClick={submit}
        disabled={loading || !code.trim() || !errorMsg.trim()}
        className="self-start rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {loading ? "Debugging..." : "Debug Code"}
      </button>
      <ErrorBanner error={error} />
      {result && (
        <div className="rounded-lg border border-slate-700 bg-slate-900 p-4">
          <MarkdownRenderer content={result} />
        </div>
      )}
    </div>
  );
}

export default function ChatInterface() {
  const [activeTab, setActiveTab] = useState("generate");

  return (
    <div className="mx-auto w-full max-w-3xl">
      <div className="mb-4 flex gap-2 rounded-lg bg-slate-800 p-1">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 rounded-md py-2 text-sm font-medium capitalize transition ${
              activeTab === tab
                ? "bg-indigo-600 text-white"
                : "text-slate-300 hover:bg-slate-700"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {activeTab === "generate" && <GenerateTab />}
      {activeTab === "review" && <ReviewTab />}
      {activeTab === "debug" && <DebugTab />}
    </div>
  );
}
