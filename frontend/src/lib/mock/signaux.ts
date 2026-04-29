import type { SignalEvent } from "../types/dem";

const types: SignalEvent["signal_type"][] = [
  "balo_operation",
  "cession",
  "bodacc_event",
  "amf_decision",
  "mandat_change",
  "press_mention",
  "procedure_collective",
];

const severityByType: Record<SignalEvent["signal_type"], SignalEvent["severity"]> = {
  balo_operation: "HIGH",
  cession: "HIGH",
  bodacc_event: "MEDIUM",
  amf_decision: "HIGH",
  mandat_change: "MEDIUM",
  press_mention: "LOW",
  procedure_collective: "CRITICAL",
};

const titles: Record<SignalEvent["signal_type"], string[]> = {
  balo_operation: [
    "Annonce d'OPA sur",
    "Augmentation de capital de",
    "Distribution de dividendes par",
    "Programme de rachat d'actions de",
    "Convocation à l'assemblée générale de",
  ],
  cession: ["Cession partielle de", "Cession totale de", "Vente d'actifs par"],
  bodacc_event: [
    "Modification statutaire de",
    "Changement de dénomination de",
    "Transfert de siège de",
  ],
  amf_decision: [
    "Sanction AMF prononcée contre",
    "Avertissement AMF à",
    "Décision AMF concernant",
  ],
  mandat_change: [
    "Nomination de nouveau président chez",
    "Démission du DG de",
    "Cooptation administrateur chez",
  ],
  press_mention: [
    "Mediapart : enquête sur",
    "Les Echos : profil de",
    "Le Monde : article sur",
  ],
  procedure_collective: [
    "Procédure collective ouverte au TC pour",
    "Redressement judiciaire de",
    "Liquidation de",
  ],
};

const denominations = [
  "Acme Industries SAS",
  "Beta Pharma Holding",
  "Carbon Capture Tech",
  "Edenred France",
  "TechVision SAS",
  "BioMed Solutions",
  "Quantum Labs",
  "Green Energy Corp",
  "Smart Mobility",
  "DataFlow Analytics",
];

const sirens = [
  "838291045",
  "432198765",
  "891234567",
  "489123456",
  "111222333",
  "222333444",
  "333444555",
  "444555666",
  "555666777",
  "666777888",
];

export const mockSignaux: SignalEvent[] = Array.from({ length: 50 }, (_, i) => {
  const type = types[i % types.length];
  const titlePool = titles[type];
  const denomIdx = i % denominations.length;
  const minutes_ago = i * 23 + Math.floor(Math.random() * 30);
  const date = new Date(Date.now() - minutes_ago * 60 * 1000);

  return {
    signal_uid: `mock_${type}_${i}`,
    signal_type: type,
    severity: severityByType[type],
    date_event: date.toISOString(),
    date_published: date.toISOString(),
    siren: sirens[denomIdx],
    denomination: denominations[denomIdx],
    title: `${titlePool[i % titlePool.length]} ${denominations[denomIdx]}`,
    description: `Description courte de l'événement ${type}. Source: référence officielle disponible. Détails dans le payload JSONB pour audit complet.`,
    source_table: `silver.${type}s`,
    source_url: `https://www.example-source.gouv.fr/event/${i}`,
  };
});
