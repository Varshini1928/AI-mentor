"use client";

export default function CodeEditor({
  value,
  onChange,
  placeholder,
  rows = 12,
  label,
}) {
  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label className="text-sm font-medium text-slate-300">{label}</label>
      )}
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        rows={rows}
        spellCheck={false}
        className="w-full resize-y rounded-lg border border-slate-700 bg-slate-950 p-3 font-mono text-sm text-slate-100 placeholder-slate-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
      />
    </div>
  );
}
