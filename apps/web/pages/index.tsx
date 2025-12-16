import { useState } from "react";
import { signIn, signOut, useSession } from "next-auth/react";
import { apiGetMe, User } from "../lib/api";

export default function Home() {
  const { data: session, status } = useSession();
  const [userProfile, setUserProfile] = useState<User | null>(null);
  const idToken = (session as any)?.id_token as string | undefined;

  const onMe = async () => {
    if (!idToken) return;
    try {
      const me = await apiGetMe(idToken);
      setUserProfile(me);
    } catch (e) {
      alert("Failed to fetch user");
    }
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

            {userProfile && (
              <div style={{ marginTop: 16, padding: 16, border: "1px solid #ccc", borderRadius: 8 }}>
                <h3>User Profile (Loaded from API)</h3>
                {userProfile.avatar_url && (
                  <img src={userProfile.avatar_url} alt="Avatar" style={{ width: 50, height: 50, borderRadius: "50%" }} />
                )}
                <div><strong>ID:</strong> {userProfile.account_id}</div>
                <div><strong>Name:</strong> {userProfile.display_name}</div>
                <div><strong>Email:</strong> {userProfile.email}</div>
              </div>
            )}
          </div>

          <div style={{ marginTop: 24 }}>
            <a href="/match/1">Go to Match WS test (match_id=1)</a>
          </div>
        </>
      )}
    </div>
  );
}
