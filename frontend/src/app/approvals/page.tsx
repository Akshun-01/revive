import { Micro } from "@/components/ui";
import { ApprovalsInbox } from "@/components/ApprovalsInbox";

export default function ApprovalsPage() {
  return (
    <div className="mx-auto max-w-[960px] px-6 py-10">
      <div className="mb-8 flex flex-col gap-3">
        <Micro>Human-in-the-loop</Micro>
        <h1 className="text-[28px] font-semibold leading-tight tracking-tight">Pending approvals</h1>
        <p className="max-w-[64ch] text-[14.5px] leading-relaxed text-ink-2">
          External and financial actions wait here until you approve them. Nothing reaches a customer without your sign-off.
        </p>
      </div>
      <ApprovalsInbox />
    </div>
  );
}
