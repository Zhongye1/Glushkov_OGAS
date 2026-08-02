import { RUNTIME_HOSTS } from "@ogas/shared";

export default function HomePage() {
  return (
    <main>
      <h1>OGAS Web</h1>
      <p>运行宿主：{RUNTIME_HOSTS.join(" / ")}</p>
    </main>
  );
}
