import { cookies } from "next/headers";
import Link from "next/link";

export async function Nav() {
  const cookieStore = await cookies();
  const hasSession = Boolean(cookieStore.get("agora_session"));

  return (
    <header className="nav">
      <Link className="brand" href="/projects">
        Agora
        <span>Team AI context</span>
      </Link>
      <nav className="nav-links" aria-label="Primary">
        <Link href="/projects">Projects</Link>
        <Link href="/users">Users</Link>
        {hasSession ? (
          <form className="inline-form" action="/logout" method="post">
            <button type="submit" className="secondary">Sign out</button>
          </form>
        ) : (
          <Link href="/login">Sign in</Link>
        )}
      </nav>
    </header>
  );
}
