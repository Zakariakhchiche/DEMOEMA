/**
 * Page Méthodologie & Sources — transparence client-facing (SaaS).
 * Explique d'où viennent les données et comment elles sont calculées.
 * Route : /methodologie (standalone, hors shell hash-routing).
 */
"use client";

import Link from "next/link";

const SOURCES: [string, string, string][] = [
  ["INPI RNE + Comptes", "INPI", "Dirigeants, mandats, bilans (CA, résultat, EBITDA)"],
  ["INSEE / SIRENE", "INSEE", "Identité, NAF, capital, état, effectif"],
  ["BODACC", "DILA / Journal Officiel", "Procédures collectives, cessions, ventes"],
  ["DVF", "DGFiP", "Transactions immobilières (prix, surfaces)"],
  ["OpenSanctions / ICIJ", "OpenSanctions, ICIJ", "Sanctions OFAC/UE/UK/ONU, offshore, PEP"],
  ["OSINT", "Scan web", "Présence digitale, domaine"],
];

const RATIOS: [string, string][] = [
  ["Marge EBITDA", "EBITDA / CA"],
  ["Marge nette", "Résultat net / CA"],
  ["ROA", "Résultat net / Total actif"],
  ["Dette / EBITDA", "Emprunts & dettes / EBITDA"],
  ["Dette / Fonds propres", "Emprunts & dettes / Capitaux propres"],
  ["Ratio d'endettement", "(Total actif − Capitaux propres) / Total actif"],
  ["Couverture des intérêts", "Résultat exploitation / Charges d'intérêts"],
  ["DSO (clients)", "Créances clients / CA × 365"],
  ["DPO (fournisseurs)", "Dettes fournisseurs / Achats × 365"],
  ["BFR (jours)", "(Stocks + Créances) / CA × 365"],
  ["Croissance CA", "(CA n − CA n-1) / CA n-1"],
];

const NATURES: [string, string, string][] = [
  ["🟢 Sourcée", "var(--accent-emerald, #34d399)", "Valeur officielle directe : identité, CA, résultat, bilan, BODACC, DVF, sanctions."],
  ["🟡 Calculée", "var(--accent-amber, #fbbf24)", "Dérivée de données réelles : ratios financiers, deal score, tiers (formules ci-dessous)."],
  ["🟠 Estimée / générée", "var(--accent-blue, #60a5fa)", "Explicitement étiquetée : EV indicative, emails candidats « à vérifier »."],
];

function Card({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{
      background: "rgba(255,255,255,0.02)", border: "1px solid var(--border-subtle, rgba(255,255,255,0.08))",
      borderRadius: 12, padding: "20px 24px", ...style,
    }}>{children}</div>
  );
}

export default function MethodologiePage() {
  return (
    <div style={{ minHeight: "100vh", background: "var(--bg-base, #0a0a0c)", color: "var(--text-primary, #f0f0f2)", padding: "40px 24px" }}>
      <div style={{ maxWidth: 920, margin: "0 auto", display: "flex", flexDirection: "column", gap: 28 }}>
        {/* Header */}
        <div>
          <Link href="/" style={{ fontSize: 13, color: "var(--accent-blue, #60a5fa)", textDecoration: "none" }}>← Retour</Link>
          <h1 style={{ fontSize: 30, fontWeight: 700, margin: "10px 0 6px", letterSpacing: "-0.02em" }}>Méthodologie & Sources</h1>
          <p style={{ fontSize: 14.5, color: "var(--text-secondary, #b0b0b8)", lineHeight: 1.6, maxWidth: 720 }}>
            Origin n'affiche que de la <strong>donnée réelle</strong> (issue de sources publiques officielles
            françaises) ou <strong>calculée à partir de données réelles</strong>. Chaque chiffre est traçable
            jusqu'à sa source ou sa formule. Aucune valeur n'est inventée.
          </p>
        </div>

        {/* Preuve */}
        <Card style={{ background: "rgba(52,211,153,0.05)", borderColor: "rgba(52,211,153,0.20)" }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: "var(--accent-emerald, #34d399)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 8 }}>Preuve d'exactitude</div>
          <p style={{ fontSize: 14, color: "var(--text-secondary)", lineHeight: 1.6, margin: 0 }}>
            Nos valeurs sont croisées avec <code>recherche-entreprises.api.gouv.fr</code> (API officielle de l'État).
            Sur un échantillon aléatoire : <strong>code NAF 97,5 % exact</strong>, <strong>résultat net identique au centime</strong>,
            <strong> chiffre d'affaires 88,6 % exact à ±5 %</strong> (le résidu = comptes sociaux vs consolidés sur les groupes).
          </p>
        </Card>

        {/* Sources */}
        <div>
          <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 12 }}>Sources de données</h2>
          <Card>
            <div style={{ display: "grid", gridTemplateColumns: "1.1fr 1fr 1.6fr", gap: "10px 16px", fontSize: 13.5 }}>
              <div style={{ fontWeight: 600, color: "var(--text-tertiary)" }}>Source</div>
              <div style={{ fontWeight: 600, color: "var(--text-tertiary)" }}>Fournisseur</div>
              <div style={{ fontWeight: 600, color: "var(--text-tertiary)" }}>Données</div>
              {SOURCES.map(([s, f, d]) => (
                <div key={s} style={{ display: "contents" }}>
                  <div style={{ fontWeight: 600 }}>{s}</div>
                  <div style={{ color: "var(--text-secondary)" }}>{f}</div>
                  <div style={{ color: "var(--text-secondary)" }}>{d}</div>
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* 3 natures */}
        <div>
          <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 12 }}>Les 3 natures de donnée</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {NATURES.map(([t, c, d]) => (
              <Card key={t} style={{ borderLeft: `3px solid ${c}` }}>
                <div style={{ fontWeight: 700, color: c, marginBottom: 4 }}>{t}</div>
                <div style={{ fontSize: 13.5, color: "var(--text-secondary)", lineHeight: 1.5 }}>{d}</div>
              </Card>
            ))}
          </div>
        </div>

        {/* Financier */}
        <div>
          <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 12 }}>Données financières (liasse INPI)</h2>
          <Card>
            <p style={{ fontSize: 13.5, color: "var(--text-secondary)", lineHeight: 1.6, marginTop: 0 }}>
              Extraites des bilans déposés à l'INPI (codes CERFA). Le <strong>chiffre d'affaires</strong> = code <strong>FJ</strong>
              (CA net, validé au centime contre la source officielle). L'<strong>EBITDA</strong> est le vrai EBITDA comptable :
            </p>
            <div style={{ fontFamily: "monospace", fontSize: 14, background: "rgba(255,255,255,0.04)", padding: "10px 14px", borderRadius: 8, color: "var(--accent-emerald)" }}>
              EBITDA = Résultat d'exploitation (EBIT) + Dotations aux amortissements & provisions
            </div>
          </Card>
        </div>

        {/* Ratios */}
        <div>
          <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 12 }}>Ratios financiers (calculés sur données réelles)</h2>
          <Card>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1.4fr", gap: "8px 16px", fontSize: 13.5 }}>
              {RATIOS.map(([r, f]) => (
                <div key={r} style={{ display: "contents" }}>
                  <div style={{ fontWeight: 600 }}>{r}</div>
                  <div className="dem-mono" style={{ color: "var(--text-secondary)", fontSize: 12.5 }}>{f}</div>
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* Scoring */}
        <div>
          <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 12 }}>Deal Score (méthodologie propriétaire)</h2>
          <Card>
            <p style={{ fontSize: 13.5, color: "var(--text-secondary)", lineHeight: 1.6, marginTop: 0 }}>
              Score 0-100 combinant 4 axes (chacun calculé sur données réelles) : <strong>Transmission</strong> (âge dirigeant, patrimoine SCI),
              <strong> Attractivity</strong> (marge, stabilité), <strong>Scale</strong> (CA), <strong>Structure</strong> (forme, holding, mandats).
            </p>
            <div style={{ fontFamily: "monospace", fontSize: 14, background: "rgba(255,255,255,0.04)", padding: "10px 14px", borderRadius: 8, color: "var(--accent-blue)" }}>
              deal_score = (Transmission × Attractivity × Scale)^⅓ × multiplicateur_de_risque
            </div>
            <p style={{ fontSize: 12.5, color: "var(--text-tertiary)", marginBottom: 0, marginTop: 10 }}>
              Tier par percentile : A·Hot = top 1 %, B·Warm = top 5 %, etc. L'EV indicative est une estimation de valorisation (étiquetée comme telle).
            </p>
          </Card>
        </div>

        {/* Périmètres */}
        <div>
          <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 12 }}>Périmètres & limites</h2>
          <Card>
            <ul style={{ fontSize: 13.5, color: "var(--text-secondary)", lineHeight: 1.7, margin: 0, paddingLeft: 18 }}>
              <li><strong>Comptes sociaux</strong> (par entité légale), pas consolidés : les groupes/holdings peuvent différer de leurs comptes consolidés publiés.</li>
              <li><strong>Dernier exercice déposé</strong> : l'année varie selon la société (un léger écart vient souvent de l'exercice retenu).</li>
              <li><strong>Couverture CA ~32 %</strong> : beaucoup de PME/SCI/holdings ne déposent pas de comptes publics — réalité du dépôt légal en France.</li>
            </ul>
          </Card>
        </div>

        <div style={{ fontSize: 12, color: "var(--text-muted)", textAlign: "center", padding: "16px 0 8px" }}>
          Origin — données issues exclusivement de sources publiques officielles françaises · calculs déterministes documentés.
        </div>
      </div>
    </div>
  );
}
