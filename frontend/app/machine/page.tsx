import PlaceholderPage from "@/components/PlaceholderPage";

export default function Page() {
  return (
    <PlaceholderPage
      title="機台管理"
      subtitle="MACHINE MANAGEMENT · 機台狀態、保養與可用產能"
      apiPath="/api/machines"
    />
  );
}
