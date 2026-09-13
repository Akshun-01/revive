import { Micro } from "@/components/ui";
import { LostRenewals } from "@/components/LostRenewals";
import { StartInvestigation } from "@/components/StartInvestigation";
import { RecentInvestigations } from "@/components/RecentInvestigations";

export default function Home() {
  return (
    <div className="mx-auto max-w-[1440px] px-6 py-10">
      <div className="mb-8 flex flex-col gap-3">
        <Micro>Non-renewal recovery</Micro>
        <h1 className="max-w-[24ch] text-[34px] font-semibold leading-[1.08] tracking-tight">
          These customers didn&apos;t renew. Find out why, and whether they&apos;re worth chasing.
        </h1>
        <p className="max-w-[64ch] text-[14.5px] leading-relaxed text-ink-2">
          Revive reads Stripe, HubSpot, Slack and Userlens, builds an evidence chain, names the cause, decides if recovery is
          rational, takes the safe actions, and asks you before anything reaches the customer.
        </p>
      </div>
      <div className="flex flex-col gap-5">
        <LostRenewals />
        <StartInvestigation />
        <RecentInvestigations />
      </div>
    </div>
  );
}
