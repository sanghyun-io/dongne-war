export async function onRequest(context) {
  const url = new URL(context.request.url)
  const lng = url.searchParams.get('lng')
  const lat = url.searchParams.get('lat')

  if (!lng || !lat) {
    return new Response(JSON.stringify({ error: 'lng, lat required' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    })
  }

  const apiKey = context.env.VWORLD_API_KEY
  if (!apiKey) {
    return new Response(JSON.stringify({ error: 'VWORLD_API_KEY not configured' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    })
  }

  try {
    const apiUrl = `https://api.vworld.kr/req/address?service=address&request=getAddress&version=2.0&key=${apiKey}&point=${lng},${lat}&crs=epsg:4326&type=BOTH&format=json&simple=false`

    const res = await fetch(apiUrl)
    const data = await res.text()

    return new Response(data, {
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'public, max-age=86400',
      },
    })
  } catch (e) {
    return new Response(JSON.stringify({ error: e.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    })
  }
}
