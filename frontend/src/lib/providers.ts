// Per-provider connect-form configuration (Settings → Integrations).
import type { Provider } from "./types";

export interface ProviderConfig {
  id: Provider;
  name: string;
  role: string;
  fieldLabel: string;
  credentialKey: string;
  prefixHint: string;
  placeholder: string;
  help: string;
}

export const PROVIDERS: ProviderConfig[] = [
  {
    id: "stripe", name: "Stripe", role: "Financial reality: subscriptions, invoices, payment state",
    fieldLabel: "Stripe Secret Key", credentialKey: "api_key", prefixHint: "sk_", placeholder: "sk_test_…",
    help: "Stripe Dashboard → Developers → API keys",
  },
  {
    id: "hubspot", name: "HubSpot", role: "Commercial context: companies, contacts, deals, notes, tasks",
    fieldLabel: "Private App Token", credentialKey: "token", prefixHint: "pat-", placeholder: "pat-…",
    help: "HubSpot → Settings → Integrations → Private Apps",
  },
  {
    id: "slack", name: "Slack", role: "Internal context: account discussions and owner notifications",
    fieldLabel: "Bot User OAuth Token", credentialKey: "token", prefixHint: "xoxb-", placeholder: "xoxb-…",
    help: "api.slack.com → Your App → OAuth & Permissions",
  },
];
