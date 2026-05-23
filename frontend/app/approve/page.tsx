import PlaceholderPage from "@/components/PlaceholderPage";

export default function Page() {
  return (
    <PlaceholderPage
      title="簽核管理"
      subtitle="APPROVAL MANAGEMENT · 待簽核與簽核歷程"
      apiPath="/api/orders/:id/actions"
    />
  );
}
