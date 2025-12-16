import Link from "next/link";
import { signIn, signOut, useSession } from "next-auth/react";
import styles from "../styles/Navbar.module.css";

export default function Navbar() {
  const { data: session, status } = useSession();

  return (
    <nav className={styles.navbar}>
      <Link href="/">
        <span className={styles.logo}>Agentic Baseball Simulator</span>
      </Link>

      <div className={styles.userSection}>
        {status === "authenticated" ? (
          <>
            <span className={styles.userInfo}>
              {session.user?.name || session.user?.email}
            </span>
            <button className={styles.logoutButton} onClick={() => signOut()}>
              Sign Out
            </button>
          </>
        ) : (
          <button className={styles.loginButton} onClick={() => signIn("google")}>
            Sign In with Google
          </button>
        )}
      </div>
    </nav>
  );
}
