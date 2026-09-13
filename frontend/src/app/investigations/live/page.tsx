import { LiveRun } from "@/components/LiveRun";

export default async function LiveRunPage(props: PageProps<"/investigations/live">) {
  const sp = await props.searchParams;
  const customer = typeof sp.customer === "string" ? sp.customer : "";
  return <LiveRun customer={customer} />;
}
