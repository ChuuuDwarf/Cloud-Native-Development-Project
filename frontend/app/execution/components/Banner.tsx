import type { Banner as BannerData } from "../types";
import { bannerStyle } from "../styles";

export default function Banner({ msg }: Readonly<{ msg: BannerData }>) {
  return (
    <div style={bannerStyle(msg.ok)}>
      {msg.ok ? "✅ " : "⚠️ "}
      {msg.text}
    </div>
  );
}
