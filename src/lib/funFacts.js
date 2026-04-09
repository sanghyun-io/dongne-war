/**
 * 업종별 카운트 데이터로 재미있는 팩트를 생성합니다.
 */

const CATEGORY_LABELS = {
  chicken: '치킨집',
  cafe: '카페',
  convenience: '편의점',
  realestate: '부동산',
  pharmacy: '약국',
  pcroom: 'PC방',
}

export function generateFunFact(data) {
  const entries = Object.entries(data)
    .filter(([, v]) => v > 0)
    .sort((a, b) => b[1] - a[1])

  if (entries.length === 0) return null

  const [topKey, topVal] = entries[0]
  const facts = []

  // 1위 업종 관련
  if (topKey === 'cafe' && data.chicken > 0) {
    const ratio = (topVal / data.chicken).toFixed(1)
    facts.push(`카페가 치킨집보다 ${ratio}배 많은 동네`)
  }

  if (topKey === 'chicken' && data.cafe > 0) {
    facts.push(`카페보다 치킨집이 더 많은 희귀한 동네!`)
  }

  if (data.realestate > data.pharmacy) {
    const ratio = (data.realestate / Math.max(data.pharmacy, 1)).toFixed(1)
    facts.push(`부동산이 약국보다 ${ratio}배 많은 동네`)
  }

  if (data.convenience > 0 && data.pcroom > 0) {
    const ratio = (data.convenience / data.pcroom).toFixed(1)
    facts.push(`편의점 ${ratio}개당 PC방 1개 꼴`)
  }

  if (data.chicken > 0 && data.pharmacy > 0) {
    const ratio = (data.chicken / data.pharmacy).toFixed(1)
    facts.push(`약국 1개당 치킨집 ${ratio}개`)
  }

  // 가게 총합
  const total = entries.reduce((sum, [, v]) => sum + v, 0)
  if (total > 0) {
    facts.push(`이 동네에만 총 ${total.toLocaleString()}개의 가게가!`)
  }

  // 랜덤 선택 (항상 같은 데이터면 같은 결과를 위해 해시 기반)
  const seed = Object.values(data).reduce((a, b) => a + b, 0)
  return facts[seed % facts.length] || facts[0]
}
