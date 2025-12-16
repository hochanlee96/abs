import { signIn, signOut, useSession } from "next-auth/react";
import { apiGetMe } from "../lib/api";

export default function Home() {
  const { data: session, status } = useSession();
  const idToken = (session as any)?.id_token as string | undefined;

  const onMe = async () => {
    if (!idToken) return;
    const me = await apiGetMe(idToken);
    alert(JSON.stringify(me, null, 2));
  };

  return (
    <div style={{ padding: 24, fontFamily: "system-ui" }}>
      <h1>Baseball Sim MVP</h1>

      {status !== "authenticated" ? (
        <button onClick={() => signIn("google")}>Sign in with Google</button>
      ) : (
        <>
          <div style={{ marginTop: 12 }}>
            <div>Signed in as: {session?.user?.email}</div>
            <button onClick={onMe} style={{ marginRight: 8 }}>Call /me</button>
            <button onClick={() => signOut()}>Sign out</button>
          </div>

          <div style={{ marginTop: 24 }}>
            <a href="/match/1">Go to Match WS test (match_id=1)</a>
          </div>
        </>
      )}
    </div>
  );
}
