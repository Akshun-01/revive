import type {
  ActionType, CauseCategory, EvidenceSource, InterventionType, InvestigationStatus, Recoverability,
} from "./types";

export const CAUSE_LABEL: Record<CauseCategory, string> = {
  product_adoption: "Product-value failure",
  pricing: "Pricing / commercial objection",
  payment: "Payment / billing issue",
  organizational_change: "Organizational change",
  customer_support: "Product / service dissatisfaction",
  product_fit: "Poor product fit",
  insufficient_evidence: "Insufficient evidence",
  other: "Other",
};

export const RECOVERABILITY_LABEL: Record<Recoverability, string> = {
  recoverable: "Recover",
  not_recoverable: "Do not pursue",
  insufficient_evidence: "Monitor",
};

export const INTERVENTION_LABEL: Record<InterventionType, string> = {
  billing_intervention: "Billing follow-up",
  targeted_onboarding: "CSM recovery + targeted onboarding",
  commercial_review: "Commercial review",
  stakeholder_reengagement: "Identify new stakeholder",
  support_escalation: "Resolve blockers first",
  do_not_pursue: "Do not pursue",
};

export const ACTION_LABEL: Record<ActionType, string> = {
  create_crm_task: "HubSpot task",
  send_internal_notification: "Slack notification",
  update_crm: "CRM update",
  send_customer_message: "Customer email",
  financial_mutation: "Financial change",
};

export const SOURCE_LABEL: Record<EvidenceSource, string> = {
  stripe: "Stripe",
  hubspot: "HubSpot",
  slack: "Slack",
  userlens: "Userlens",
};

export const SOURCE_ROLE: Record<EvidenceSource, string> = {
  stripe: "Financial reality",
  hubspot: "Commercial context",
  slack: "Internal context",
  userlens: "Product behavior",
};

export const STATUS_LABEL: Record<InvestigationStatus, string> = {
  created: "Queued",
  running: "Investigating",
  waiting_for_approval: "Awaiting approval",
  completed: "Complete",
  rejected: "Rejected",
  failed: "Failed",
};

export function money(n: number | null | undefined, currency = "USD"): string {
  if (n == null) return "—";
  return new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 0 }).format(n);
}

export function pct(n: number | null | undefined): string {
  if (n == null) return "—";
  return `${Math.round(n * 100)}%`;
}

export function shortDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export function clock(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
}
