import { Workspace } from "@/components/Workspace";

export default async function InvestigationPage(props: PageProps<"/investigations/[id]">) {
  const { id } = await props.params;
  const sp = await props.searchParams;
  const customer = typeof sp.customer === "string" ? sp.customer : undefined;
  return <Workspace id={id} customerHint={customer} />;
}
