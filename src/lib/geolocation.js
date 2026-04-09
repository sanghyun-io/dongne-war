const VWORLD_API_KEY = import.meta.env.VITE_VWORLD_API_KEY || ''

export function isAvailable() {
  return !!VWORLD_API_KEY && !!navigator.geolocation
}

export function getPosition() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('위치 정보를 지원하지 않는 브라우저입니다.'))
      return
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      (err) => {
        if (err.code === 1) reject(new Error('위치 정보 접근이 거부되었습니다.'))
        else if (err.code === 2) reject(new Error('위치 정보를 가져올 수 없습니다.'))
        else reject(new Error('위치 정보 요청 시간이 초과되었습니다.'))
      },
      { enableHighAccuracy: false, timeout: 10000 },
    )
  })
}

export async function reverseGeocode(lat, lng) {
  if (!VWORLD_API_KEY) throw new Error('브이월드 API 키가 설정되지 않았습니다.')

  const url = new URL('https://api.vworld.kr/req/address')
  url.searchParams.set('service', 'address')
  url.searchParams.set('request', 'getAddress')
  url.searchParams.set('version', '2.0')
  url.searchParams.set('key', VWORLD_API_KEY)
  url.searchParams.set('point', `${lng},${lat}`)
  url.searchParams.set('crs', 'epsg:4326')
  url.searchParams.set('type', 'BOTH')
  url.searchParams.set('format', 'json')
  url.searchParams.set('simple', 'false')

  const res = await fetch(url)
  if (!res.ok) throw new Error('역지오코딩 요청에 실패했습니다.')

  const data = await res.json()
  if (data.response?.status !== 'OK') {
    throw new Error('역지오코딩 결과가 없습니다.')
  }

  const results = Array.isArray(data.response.result)
    ? data.response.result
    : [data.response.result]

  let sido = ''
  let sigungu = ''
  let adminDong = ''
  let legalDong = ''

  for (const r of results) {
    const s = r?.structure
    if (!s) continue
    if (!sido && s.level1) sido = s.level1
    if (!sigungu && s.level2) sigungu = s.level2
    if (!legalDong && s.level4L) legalDong = s.level4L
    if (!adminDong && s.level4A) adminDong = s.level4A
  }

  if (!sido || !sigungu) throw new Error('주소를 확인할 수 없습니다.')

  return { sido, sigungu, adminDong, legalDong }
}

/**
 * 역지오코딩 결과를 district_counts.json 데이터와 매칭
 * @returns {{ level: 'dong'|'district'|'city'|'none', city?, district?, dong? }}
 */
export function matchLocation(districtData, { sido, sigungu, adminDong, legalDong }) {
  const cityData = districtData[sido]
  if (!cityData) return { level: 'none' }

  const districtObj = cityData[sigungu]
  if (!districtObj) return { level: 'city', city: sido }

  // 행정동 먼저, 법정동 순서로 매칭
  if (adminDong && districtObj[adminDong]) {
    return { level: 'dong', city: sido, district: sigungu, dong: adminDong }
  }
  if (legalDong && districtObj[legalDong]) {
    return { level: 'dong', city: sido, district: sigungu, dong: legalDong }
  }

  // 동 매칭 실패 → 시군구 동 선택으로
  return { level: 'district', city: sido, district: sigungu }
}
