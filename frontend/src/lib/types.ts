// Types mirror the backend API contract v0.1 (API.md). Enum strings are verbatim.

export type InvestigationStatus =
  | "created" | "running" | "waiting_for_approval" | "completed" | "rejected" | "failed";

export type EvidenceSource = "stripe" | "hubspot" | "slack" | "userlens";
export type EvidenceCategory = "billing" | "product_behavior" | "crm" | "communication";

export type CauseCategory =
  | "product_adoption" | "pricing" | "payment" | "organizational_change"
  | "customer_support" | "product_fit" | "insufficient_evidence" | "other";

export type Recoverability = "recoverable" | "not_recoverable" | "insufficient_evidence";

export type InterventionType =
  | "billing_intervention" | "targeted_onboarding" | "commercial_review"
  | "stakeholder_reengagement" | "support_escalation" | "do_not_pursue";

export type ActionType =
  | "create_crm_task" | "send_internal_notification" | "update_crm"
  | "send_customer_message" | "financial_mutation";

export type ActionStatus = "proposed" | "approved" | "rejected" | "executed" | "failed" | "verified";
export type ApprovalStatus = "pending" | "approved" | "rejected";

export interface Customer {
  id: string;
  name: string;
  annual_revenue: number | null;
  currency: string;
  renewal_date: string | null;
  renewal_status: string | null;
  owner_id: string | null;
  owner_name: string | null;
  external_ids: Record<string, string>;
}

export interface Evidence {
  id: string;
  source: EvidenceSource;
  category: EvidenceCategory;
  title: string;
  finding: string;
  source_reference: string | null;
  timestamp: string | null;
  confidence: number;
  supports: CauseCategory[];
  contradicts: CauseCategory[];
}

export interface CauseHypothesis {
  category: CauseCategory;
  confidence: number;
  supporting_evidence_ids: string[];
  contradicting_evidence_ids: string[];
  reasoning: string;
}

export interface Diagnosis {
  primary_cause: CauseHypothesis;
  alternatives: CauseHypothesis[];
  confidence: number;
}

export interface RecoverabilityDecision {
  decision: Recoverability;
  confidence: number;
  factors: Record<string, number>;
  reasoning: string;
  supporting_evidence_ids: string[];
}

export interface Intervention {
  type: InterventionType;
  priority: "low" | "medium" | "high";
  reason: string;
  expected_outcome: string;
  risk: string;
  supporting_evidence_ids: string[];
  approval_required: boolean;
}

export interface ActionResult {
  action_id: string;
  success: boolean;
  external_reference: string | null;
  message: string | null;
  executed_at: string;
}

export interface Action {
  id: string;
  type: ActionType;
  description: string;
  parameters: Record<string, unknown>;
  approval_required: boolean;
  status: ActionStatus;
  result?: ActionResult | null;
}

export interface VerificationResult {
  action_id: string;
  verified: boolean;
  expected_state: Record<string, unknown>;
  actual_state: Record<string, unknown>;
  discrepancies: string[];
  verified_at: string;
}

export interface Investigation {
  id: string;
  status: InvestigationStatus;
  customer: Customer | null;
  revenue_impact: number | null;
  evidence: Evidence[];
  diagnosis: Diagnosis | null;
  recoverability: RecoverabilityDecision | null;
  intervention: Intervention | null;
  actions: Action[];
  verification: VerificationResult[];
  pending_action: Action | null;
  warnings: string[];
  created_at: string;
  completed_at: string | null;
}

export interface Approval {
  id: string;
  investigation_id: string;
  action: Action;
  status: ApprovalStatus;
  created_at: string;
}

export type EventName =
  | "customer_resolved" | "evidence_source_started" | "evidence_source_completed"
  | "diagnosis_started" | "diagnosis_completed" | "approval_required"
  | "action_executed" | "action_verified" | "investigation_completed";

export interface InvestigationEvent {
  id?: string; // sequence id when the transport provides one; used for de-duplication
  name: EventName;
  data: Record<string, unknown>;
  at: string; // client receive time, ISO
}

export type Provider = "stripe" | "hubspot" | "slack";

export interface Connection {
  id: string;
  provider: Provider;
  status: string;
  scopes: string[];
  created_at: string;
  updated_at: string;
}

export interface StartResponse {
  investigation_id: string;
  status: InvestigationStatus;
}

export interface ReviveClient {
  health(): Promise<{ status: string; data_source?: string; llm_provider?: string }>;
  startInvestigation(customer: string): Promise<StartResponse>;
  getInvestigation(id: string): Promise<Investigation>;
  /** Subscribe to the SSE stream. Returns an unsubscribe function. */
  subscribe(id: string, onEvent: (e: InvestigationEvent) => void, onError?: (err: unknown) => void): () => void;
  listApprovals(): Promise<Approval[]>;
  approve(id: string, editedParameters?: Record<string, unknown>): Promise<{ id: string; status: ApprovalStatus }>;
  reject(id: string, reason: string): Promise<{ id: string; status: ApprovalStatus }>;
  listConnections(): Promise<Connection[]>;
  /** Create or update the connection for a provider. The secret is sent once and never returned. */
  connect(provider: Provider, credentials: Record<string, string>, scopes?: string[]): Promise<Connection>;
  disconnect(provider: Provider): Promise<void>;
}
