import { useRouter } from "next/router";
import { useSession } from "next-auth/react";
import { useEffect, useMemo, useState } from "react";

export default function MatchPage() {
  const router = useRouter();
  const { matchId } = router.query;
  const { data: session, status } = useSession();
  const idToken = (session as any)?.id_token as string | undefined;

  const [logs, setLogs] = useState<any[]>([]);
  const wsUrl = useMemo(() => {
    if (!matchId || !idToken) return null;
    const base = process.env.NEXT_PUBLIC_API_BASE_URL!.replace("http", "ws");
    return `${base}/ws/match/${matchId}?token=${encodeURIComponent(idToken)}`;
  }, [matchId, idToken]);

  useEffect(() => {
    if (!wsUrl) return;
    const ws = new WebSocket(wsUrl);
    ws.onmessage = (evt) => {
      try {
        setLogs((prev) => [...prev, JSON.parse(evt.data)]);
      } catch {
        setLogs((prev) => [...prev, evt.data]);
      }
    };
    ws.onerror = () => setLogs((prev) => [...prev, { type: "ERROR" }]);
    return () => ws.close();
  }, [wsUrl]);

  if (status !== "authenticated") {
    return <div style={{ padding: 24 }}>Sign in first.</div>;
  }

  return (
    <div style={{ padding: 24, fontFamily: "system-ui" }}>
      <h2>Match WS: {String(matchId)}</h2>
      <div style={{ marginTop: 12 }}>
        <pre>{JSON.stringify(logs, null, 2)}</pre>
      </div>
    </div>
  );
}