type PlaceholderPageProps = {
  title: string;
  subtitle: string;
  apiPath?: string;
};

export default function PlaceholderPage({ title, subtitle, apiPath }: PlaceholderPageProps) {
  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 800, letterSpacing: -0.5 }}>{title}</h1>
        <p
          style={{
            fontSize: 12,
            color: "var(--text3)",
            marginTop: 4,
            fontFamily: "monospace",
          }}
        >
          {subtitle}
        </p>
      </div>

      <div
        style={{
          background: "var(--s1)",
          border: "1px solid var(--border2)",
          borderRadius: 12,
          padding: 24,
        }}
      >
        <div style={{ fontSize: 42, marginBottom: 12 }}>🚧</div>
        <h2 style={{ fontSize: 18, fontWeight: 800, marginBottom: 8 }}>頁面施工中</h2>
        <p style={{ color: "var(--text2)", fontSize: 13, lineHeight: 1.7 }}>
          此頁已先建立路由，避免側邊欄點擊後出現 404。後續可依 API
          文件補上列表、篩選、表單與操作按鈕。
        </p>
        {apiPath && (
          <div
            style={{
              marginTop: 16,
              display: "inline-block",
              background: "var(--s2)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              padding: "8px 12px",
              fontFamily: "monospace",
              fontSize: 12,
              color: "var(--text2)",
            }}
          >
            API：{apiPath}
          </div>
        )}
      </div>
    </div>
  );
}
