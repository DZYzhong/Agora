import { cookies } from "next/headers";
import Link from "next/link";
import { apiGetWithSession } from "../../lib/api";

type User = {
  id: string;
  org_id: string;
  username: string | null;
  display_name: string;
  status: string;
  created_at: string;
};

type UsersResponse = {
  users: User[];
};

function sessionRequest(): Request {
  // Server components read cookies via next/headers; RequestCookies.toString()
  // serializes them into the Cookie header the API expects.
  return new Request("http://web", {
    headers: { cookie: cookies().toString() },
  });
}

export default async function UsersPage({
  searchParams,
}: {
  searchParams: Promise<{
    activation_token?: string;
    reset_token?: string;
    username?: string;
    error?: string;
  }>;
}) {
  const params = await searchParams;
  let users: User[] = [];
  let sessionError = false;
  try {
    const response = await apiGetWithSession<UsersResponse>("/users?org_id=local-org", sessionRequest());
    users = response.users;
  } catch {
    sessionError = true;
  }

  return (
    <main className="page">
      <h1>Users</h1>
      <p className="muted">Manage local Agora accounts. New users receive a one-time activation token.</p>

      {sessionError && (
        <p className="alert">Could not load users. Sign in first: <Link href="/login">Sign in</Link></p>
      )}

      {params.error && <p className="alert">{params.error}</p>}

      {params.activation_token && params.username && (
        <section className="panel alert-highlight">
          <h2>Deliver this one-time activation token</h2>
          <p>
            Send the following token to <strong>{params.username}</strong> over an authenticated external channel.
            It expires in 30 minutes and can only be used once.
          </p>
          <pre className="token-box">{params.activation_token}</pre>
        </section>
      )}

      {params.reset_token && params.username && (
        <section className="panel alert-highlight">
          <h2>Deliver this one-time reset token</h2>
          <p>
            Send the following token to <strong>{params.username}</strong> over an authenticated external channel.
            It expires in 15 minutes and can only be used once.
          </p>
          <pre className="token-box">{params.reset_token}</pre>
        </section>
      )}

      <form className="panel form" action="/users/create" method="post">
        <h2>Create user</h2>
        <label>
          Username
          <input name="username" placeholder="alice" required minLength={2} maxLength={64} />
        </label>
        <label>
          Display name
          <input name="display_name" placeholder="Alice" required maxLength={128} />
        </label>
        <button type="submit">Create user</button>
      </form>

      <section className="grid">
        {users.map((user) => (
          <article className="panel" key={user.id}>
            <div className="session-header">
              <div>
                <h2>{user.display_name}</h2>
                <p className="muted">{user.username ?? "(no username)"}</p>
                <p className="muted">Status: {user.status}</p>
              </div>
            </div>
            <div className="actions">
              {user.status === "active" ? (
                <form action="/users/disable" method="post">
                  <input type="hidden" name="user_id" value={user.id} />
                  <button type="submit" className="danger">Disable</button>
                </form>
              ) : (
                <form action="/users/enable" method="post">
                  <input type="hidden" name="user_id" value={user.id} />
                  <button type="submit">Enable</button>
                </form>
              )}
              <form action="/users/reset" method="post">
                <input type="hidden" name="user_id" value={user.id} />
                <button type="submit" className="secondary">Reset password</button>
              </form>
            </div>
          </article>
        ))}
      </section>

      <form className="inline-form" action="/logout" method="post">
        <button type="submit" className="secondary">Sign out</button>
      </form>
    </main>
  );
}
