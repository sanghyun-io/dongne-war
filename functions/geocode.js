export async function onRequest(context) {
  const url = new URL(context.request.url)
  const lng = url.searchParams.get('lng')
  const lat = url.searchParams.get('lat')

  if (!lng || !lat) {
    return Response.json({ error: 'lng, lat required' }, { status: 400 })
  }

  const apiKey = context.env.VWORLD_API_KEY
  if (!apiKey) {
    return Response.json({ error: 'VWORLD_API_KEY not configured' }, { status: 500 })
  }

  const apiUrl = `https://api.vworld.kr/req/address?service=address&request=getAddress&version=2.0&key=${encodeURIComponent(apiKey)}&point=${lng},${lat}&crs=epsg:4326&type=BOTH&format=json&simple=false`

  const res = await fetch(apiUrl)
  const body = await res.text()

  return new Response(body, {
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'public, max-age=86400',
    },
  })
}
