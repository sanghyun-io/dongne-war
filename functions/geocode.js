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

  const apiUrl = new URL('https://api.vworld.kr/req/address')
  apiUrl.searchParams.set('service', 'address')
  apiUrl.searchParams.set('request', 'getAddress')
  apiUrl.searchParams.set('version', '2.0')
  apiUrl.searchParams.set('key', apiKey)
  apiUrl.searchParams.set('point', `${lng},${lat}`)
  apiUrl.searchParams.set('crs', 'epsg:4326')
  apiUrl.searchParams.set('type', 'BOTH')
  apiUrl.searchParams.set('format', 'json')
  apiUrl.searchParams.set('simple', 'false')

  const res = await fetch(apiUrl.toString())
  const data = await res.text()

  return new Response(data, {
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'public, max-age=86400',
    },
  })
}
