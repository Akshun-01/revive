import { Micro } from "@/components/ui";
import { IntegrationsSettings } from "@/components/IntegrationsSettings";

export default function IntegrationsPage() {
  return (
    <div className="mx-auto max-w-[960px] px-6 py-10">
      <div className="mb-8 flex flex-col gap-3">
        <Micro>Settings · Integrations</Micro>
        <h1 className="text-[28px] font-semibold leading-tight tracking-tight">Connect your systems</h1>
        <p className="max-w-[64ch] text-[14.5px] leading-relaxed text-ink-2">
          Revive investigates with whatever is connected. Tokens are sent to the backend once and are never shown or stored here.
        </p>
      </div>
      <IntegrationsSettings />
    </div>
  );
}
