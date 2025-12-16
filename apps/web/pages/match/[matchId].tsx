import { useRouter } from 'next/router'

export default function MatchDetail() {
  const router = useRouter()
  const { matchId } = router.query

  return (
    <div>
      <h1>Match Detail</h1>
      <p>Match ID: {matchId}</p>
    </div>
  )
}
