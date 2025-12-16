export async function apiGetMe(idToken: string) {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/me`, {
    headers: { Authorization: `Bearer ${idToken}` }
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}