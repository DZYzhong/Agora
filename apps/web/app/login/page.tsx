export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const { error } = await searchParams;
  return (
    <main className="page">
      <h1>Sign in</h1>
      <p className="muted">Agora Web uses your local Agora account. Agent and CI tools keep using bearer tokens.</p>
      {error === "invalid_credentials" && (
        <p className="alert">Invalid username or password. Reauthentication may be required for approval actions.</p>
      )}
      <form className="panel form" action="/login/submit" method="post">
        <label>
          Username
          <input name="username" required autoComplete="username" />
        </label>
        <label>
          Password
          <input name="password" type="password" required autoComplete="current-password" />
        </label>
        <button type="submit">Sign in</button>
      </form>
    </main>
  );
}
