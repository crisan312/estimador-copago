"use client";
import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { Search, ArrowRight } from "lucide-react";

const SUGGESTIONS = [
  "me duele el pecho",
  "me duele la barriga",
  "tengo mareos frecuentes",
  "me duele la espalda",
  "tengo calentura",
  "me duele el oído",
  "problemas para dormir",
  "me falta el aire",
];

export default function SearchBar() {
  const [value, setValue] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(false);
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

  const filtered = SUGGESTIONS.filter((s) =>
    s.toLowerCase().includes(value.toLowerCase())
  ).slice(0, 5);

  const submit = (query: string) => {
    if (!query.trim()) return;
    router.push(`/chat?q=${encodeURIComponent(query.trim())}`);
  };

  return (
    <div className="relative w-full max-w-2xl">
      <div className="flex items-center gap-3 rounded-2xl border border-gray-200 bg-white px-4 py-3 shadow-md focus-within:border-brand-400 focus-within:ring-2 focus-within:ring-brand-100 transition-all">
        <Search className="h-5 w-5 shrink-0 text-gray-400" />
        <input
          ref={inputRef}
          type="text"
          placeholder="Describe tu síntoma o busca una especialidad..."
          className="flex-1 bg-transparent text-base text-gray-900 placeholder-gray-400 outline-none"
          value={value}
          onChange={(e) => { setValue(e.target.value); setShowSuggestions(true); }}
          onFocus={() => setShowSuggestions(true)}
          onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
          onKeyDown={(e) => { if (e.key === "Enter") submit(value); }}
        />
        <button
          onClick={() => submit(value)}
          className="flex items-center gap-1 rounded-xl bg-brand-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-brand-700 transition-colors"
        >
          Consultar <ArrowRight className="h-4 w-4" />
        </button>
      </div>

      {showSuggestions && value && filtered.length > 0 && (
        <ul className="absolute top-full z-10 mt-2 w-full rounded-xl border border-gray-100 bg-white py-1 shadow-lg">
          {filtered.map((s) => (
            <li key={s}>
              <button
                className="flex w-full items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50"
                onMouseDown={() => { setValue(s); submit(s); }}
              >
                <Search className="h-3.5 w-3.5 text-gray-400" />
                {s}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
