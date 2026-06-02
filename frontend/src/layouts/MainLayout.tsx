import { ReactNode } from "react";

export default function MainLayout({ children }: Readonly<{ children?: ReactNode }>) {
  return <div className="main-layout">{children}</div>;
}
