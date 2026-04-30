"use client";

import { useState, useEffect, useRef } from "react";
import { Icon } from "./Icon";
import { SLASH_COMMANDS } from "@/lib/dem/data";

interface Props {
  onSubmit: (text: string) => void;
  suggestions?: string[] | null;
  isStreaming?: boolean;
}

type Filters = {
  dept?: string;
  ca_min?: number;
  ca_max?: number;
  ebitda_positive?: boolean;
  effectif_min?: number;
  age_dirigeant_min?: number;
};

export function ChatInput({ onSubmit, suggestions, isStreaming }: Props) {
  const [val, setVal] = useState("");
  const [showSlash, setShowSlash] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<Filters>({});
  const ref = useRef<HTMLInputElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setShowSlash(val.startsWith("/") && val.length < 20);
  }, [val]);

  const filterPrefix = (): string => {
    const parts: string[] = [];
    if (filters.dept) parts.push(`dept=${filters.dept}`);
    if (filters.ca_min) parts.push(`ca_min=${filters.ca_min}M`);
    if (filters.ca_max) parts.push(`ca_max=${filters.ca_max}M`);
    if (filters.ebitda_positive) parts.push(`ebitda+`);
    if (filters.effectif_min) parts.push(`eff_min=${filters.effectif_min}`);
    if (filters.age_dirigeant_min) parts.push(`age_min=${filters.age_dirigeant_min}`);
    return parts.length > 0 ? `[FILTRES: ${parts.join(" ")}] ` : "";
  };

  const filtersActiveCount = (): number =>
    Object.values(filters).filter((v) => v !== undefined && v !== "" && v !== false).length;

  const handleFile = async (file: File) => {
    try {
      if (file.size > 5 * 1024 * 1024) {
        alert("Fichier trop volumineux (max 5 Mo).");
        return;
      }
      const text = await file.text();
      // Détection rapide : si CSV de SIREN, soumettre une requête de batch
      const sirens = text.match(/\b\d{9}\b/g);
      if (sirens && sirens.length > 0 && sirens.length <= 20) {
        const uniq = Array.from(new Set(sirens));
        const sample = uniq.slice(0, 10).join(", ");
        const more = uniq.length > 10 ? ` (et ${uniq.length - 10} autres)` : "";
        onSubmit(`Analyse les ${uniq.length} SIREN du fichier ${file.name} : ${sample}${more}`);
      } else {
        onSubmit(`J'ai joint le fichier ${file.name} (${(file.size / 1024).toFixed(1)} Ko). ${text.substring(0, 500)}${text.length > 500 ? "…" : ""}`);
      }
    } catch (e) {
      alert(`Erreur lecture fichier : ${e}`);
    }
  };

  const submit = () => {
    if (val.trim() && !isStreaming) {
      onSubmit(filterPrefix() + val.trim());
      setVal("");
    }
  };

  return (
    <div style={{ position: "relative", margin: "0 auto", maxWidth: 860, width: "100%" }}>
      {showSlash && (
        <div className="dem-glass-2" style={{
          position: "absolute", bottom: "calc(100% + 6px)", left: 0, right: 0,
          borderRadius: 12, padding: 6,
          boxShadow: "0 16px 48px -8px rgba(0,0,0,0.6)", zIndex: 20,
        }}>
          <div style={{
            padding: "6px 10px", fontSize: 10.5,
            color: "var(--text-tertiary)",
            textTransform: "uppercase", letterSpacing: "0.08em", fontWeight: 600,
          }}>Commandes</div>
          {SLASH_COMMANDS.map((c) => (
            <div
              key={c.cmd}
              onClick={() => { setVal(c.example + " "); setShowSlash(false); ref.current?.focus(); }}
              style={{
                display: "flex", alignItems: "center", gap: 10,
                padding: "8px 10px", borderRadius: 7,
                cursor: "pointer", fontSize: 12.5,
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.04)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
            >
              <span className="dem-mono" style={{ color: "var(--accent-purple)", fontWeight: 600, minWidth: 80 }}>{c.cmd}</span>
              <span style={{ color: "var(--text-secondary)" }}>{c.desc}</span>
              <span className="dem-mono" style={{ marginLeft: "auto", color: "var(--text-muted)", fontSize: 11 }}>{c.example}</span>
            </div>
          ))}
        </div>
      )}

      {showFilters && (
        <div
          role="dialog"
          aria-label="Filtres de recherche"
          className="dem-glass-2"
          style={{
            position: "absolute", bottom: "calc(100% + 6px)", right: 0, width: 380,
            borderRadius: 12, padding: 16, zIndex: 25,
            boxShadow: "0 16px 48px -8px rgba(0,0,0,0.6)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", marginBottom: 12 }}>
            <Icon name="filter" size={13} color="var(--accent-purple)" />
            <span style={{ marginLeft: 6, fontSize: 13, fontWeight: 600 }}>Filtres</span>
            <button
              onClick={() => { setFilters({}); }}
              className="dem-btn dem-btn-ghost"
              style={{ marginLeft: "auto", fontSize: 11 }}
            >Réinitialiser</button>
            <button
              onClick={() => setShowFilters(false)}
              className="dem-btn dem-btn-ghost dem-btn-icon"
              aria-label="Fermer"
              style={{ marginLeft: 4 }}
            >×</button>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div>
              <label style={{ fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600 }}>Département</label>
              <input
                type="text"
                value={filters.dept || ""}
                onChange={(e) => setFilters({ ...filters, dept: e.target.value || undefined })}
                placeholder="ex: 75, 92, IDF"
                style={{ width: "100%", marginTop: 4, padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border-subtle)", background: "rgba(255,255,255,0.02)", color: "var(--text-primary)", fontSize: 12 }}
              />
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600 }}>CA min (M€)</label>
                <input
                  type="number"
                  min={0}
                  value={filters.ca_min ?? ""}
                  onChange={(e) => setFilters({ ...filters, ca_min: e.target.value ? Number(e.target.value) : undefined })}
                  placeholder="10"
                  style={{ width: "100%", marginTop: 4, padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border-subtle)", background: "rgba(255,255,255,0.02)", color: "var(--text-primary)", fontSize: 12 }}
                />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600 }}>CA max (M€)</label>
                <input
                  type="number"
                  min={0}
                  value={filters.ca_max ?? ""}
                  onChange={(e) => setFilters({ ...filters, ca_max: e.target.value ? Number(e.target.value) : undefined })}
                  placeholder="100"
                  style={{ width: "100%", marginTop: 4, padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border-subtle)", background: "rgba(255,255,255,0.02)", color: "var(--text-primary)", fontSize: 12 }}
                />
              </div>
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600 }}>Effectif min</label>
                <input
                  type="number"
                  min={0}
                  value={filters.effectif_min ?? ""}
                  onChange={(e) => setFilters({ ...filters, effectif_min: e.target.value ? Number(e.target.value) : undefined })}
                  placeholder="50"
                  style={{ width: "100%", marginTop: 4, padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border-subtle)", background: "rgba(255,255,255,0.02)", color: "var(--text-primary)", fontSize: 12 }}
                />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ fontSize: 11, color: "var(--text-tertiary)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600 }}>Âge dir. min</label>
                <input
                  type="number"
                  min={0}
                  max={99}
                  value={filters.age_dirigeant_min ?? ""}
                  onChange={(e) => setFilters({ ...filters, age_dirigeant_min: e.target.value ? Number(e.target.value) : undefined })}
                  placeholder="60"
                  style={{ width: "100%", marginTop: 4, padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border-subtle)", background: "rgba(255,255,255,0.02)", color: "var(--text-primary)", fontSize: 12 }}
                />
              </div>
            </div>
            <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12.5, color: "var(--text-secondary)", cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={filters.ebitda_positive || false}
                onChange={(e) => setFilters({ ...filters, ebitda_positive: e.target.checked || undefined })}
              />
              EBITDA positif uniquement
            </label>
          </div>
        </div>
      )}

      {suggestions && suggestions.length > 0 && !val && (
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 10, justifyContent: "center" }}>
          {suggestions.map((s, i) => (
            <button key={i} className="dem-chip" onClick={() => onSubmit(s)}>
              <Icon name="sparkles" size={10} color="var(--accent-purple)" />
              {s}
            </button>
          ))}
        </div>
      )}

      <div className="dem-glass-2" style={{
        borderRadius: 14, padding: "10px 12px 10px 14px",
        display: "flex", alignItems: "center", gap: 10,
        boxShadow: "0 4px 30px -8px rgba(0,0,0,0.40)",
      }}>
        <Icon name="chat" size={14} color="var(--text-tertiary)" />
        <input
          ref={ref}
          value={val}
          onChange={(e) => setVal(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }}
          placeholder="Pose ta question ou tape / pour les commandes…"
          style={{
            flex: 1, background: "transparent", border: "none", outline: "none",
            color: "var(--text-primary)", fontSize: 14, fontFamily: "inherit",
          }}
        />
        <input
          ref={fileRef}
          type="file"
          accept=".csv,.txt,.json,.tsv"
          style={{ display: "none" }}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) handleFile(f);
            e.target.value = "";
          }}
        />
        <button
          className="dem-btn dem-btn-ghost dem-btn-icon"
          title="Joindre un fichier (CSV de SIREN, TXT, JSON)"
          aria-label="Joindre un fichier"
          onClick={() => fileRef.current?.click()}
        >
          <Icon name="paperclip" size={13} />
        </button>
        <button
          className={`dem-btn ${filtersActiveCount() > 0 ? "dem-btn-primary" : "dem-btn-ghost"}`}
          title="Filtres de recherche"
          aria-label="Ouvrir les filtres"
          aria-expanded={showFilters}
          onClick={() => setShowFilters((v) => !v)}
        >
          <Icon name="filter" size={12} /> Filtres{filtersActiveCount() > 0 ? ` · ${filtersActiveCount()}` : ""}
        </button>
        <button
          className="dem-btn dem-btn-primary"
          disabled={!val.trim() || isStreaming}
          style={{ opacity: val.trim() && !isStreaming ? 1 : 0.5 }}
          onClick={submit}
        >
          <Icon name="send" size={12} /> Send
          <span className="kbd" style={{ marginLeft: 4 }}>↵</span>
        </button>
      </div>

      <div style={{
        display: "flex", gap: 6, marginTop: 8, fontSize: 11, color: "var(--text-tertiary)",
        justifyContent: "center", alignItems: "center",
      }}>
        <span style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>
          <Icon name="pin" size={10} color="var(--accent-purple)" />
          <span>Épinglés:</span>
        </span>
        <button className="dem-chip" onClick={() => onSubmit("DD compliance Acme Industries")}>
          <Icon name="shield" size={10} /> DD compliance
        </button>
        <button className="dem-chip" onClick={() => onSubmit("Sourcing IDF chimie >20M€")}>
          <Icon name="search" size={10} /> Sourcing IDF chimie
        </button>
        <button className="dem-chip" onClick={() => onSubmit("Compare Beta et Gamma")}>
          <Icon name="layers" size={10} /> Compare cibles
        </button>
      </div>
    </div>
  );
}
