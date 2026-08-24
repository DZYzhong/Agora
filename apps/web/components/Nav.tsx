import Link from "next/link";

export function Nav() {
  return (
    <header className="nav">
      <Link className="brand" href="/">
        Agora
        <span>Team AI context</span>
      </Link>
      <nav className="nav-links" aria-label="Primary">
        <Link href="/projects">Projects</Link>
      </nav>
    </header>
  );
}
