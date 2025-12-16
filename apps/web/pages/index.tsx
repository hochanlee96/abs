import { signIn, useSession, signOut } from "next-auth/react";
import { useRouter } from "next/router";
import { useEffect } from "react";
import styles from "../styles/Landing.module.css";
// import { apiGetMe, User } from "../lib/api"; // Refactored to placeholder for now as per instructions

// Simple placeholder for the user profile to avoid direct API calls for now,
// except for the auth flow which is preserved.
const UserProfilePlaceholder = ({ user }: { user: any }) => (
  <div style={{ marginTop: 20, padding: 20, background: 'rgba(255,255,255,0.1)', borderRadius: 12 }}>
    <h3>Welcome, {user.name}!</h3>
    <p>Email: {user.email}</p>
    <button onClick={() => signOut()} style={{ marginTop: 10, padding: '8px 16px', borderRadius: 6 }}>
      Sign out
    </button>
  </div>
);

export default function Home() {
  const { data: session, status } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (status === "authenticated") {
      router.push("/character");
    }
  }, [status, router]);

  if (status === "loading" || status === "authenticated") {
    return null;
  }

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>Agentic Baseball Simulator</h1>
      <div className={styles.buttonWrapper}>
        <button className={styles.loginButton} onClick={() => signIn("google")}>
          구글로 시작하기
        </button>
      </div>
    </div>
  );
}