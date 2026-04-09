export async function onRequest(context) {
  try {
    const url = new URL(context.request.url)
    const lng = url.searchParams.get('lng')
    const lat = url.searchParams.get('lat')

    if (!lng || !lat) {
      return Response.json({ error: 'lng, lat required' }, { status: 400 })
    }

    const apiKey = context.env.VWORLD_API_KEY
    if (!apiKey) {
      return Response.json({ error: 'no key' })
    }

    const apiUrl = `https://api.vworld.kr/req/address?service=address&request=getAddress&version=2.0&key=${encodeURIComponent(apiKey)}&point=${lng},${lat}&crs=epsg:4326&type=BOTH&format=json&simple=false`

    let res
    try {
      res = await fetch(apiUrl)
    } catch (fetchErr) {
      return Response.json({ error: 'fetch failed', message: fetchErr.message })
    }

    const body = await res.text()
    return new Response(body, {
      headers: { 'Content-Type': 'application/json' },
    })
  } catch (e) {
    return Response.json({ error: 'top-level', message: e.message, stack: e.stack })
  }
}
