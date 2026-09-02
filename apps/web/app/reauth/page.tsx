export default async function ReauthPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string; error?: string }>;
}) {
  const { next, error } = await searchParams;
  return (
    <main className="page">
      <h1>Reauthenticate</h1>
      <p className="muted">
        Approval and high-risk actions require recent password confirmation. Enter your password to continue.
      </p>
      {error === "invalid_password" && <p className="alert">Incorrect password. Try again.</p>}
      <form className="panel form" action="/reauth/submit" method="post">
        {next ? <input type="hidden" name="next" value={next} /> : null}
        <label>
          Password
          <input name="password" type="password" required autoComplete="current-password" />
        </label>
        <button type="submit">Confirm</button>
      </form>
    </main>
  );
}
