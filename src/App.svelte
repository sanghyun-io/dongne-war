<script>
  import districtData from './data/district_counts.json'
  import Card from './lib/Card.svelte'
  import Share from './lib/Share.svelte'

  const KAKAO_JS_KEY = '' // developers.kakao.com에서 발급받은 JavaScript 키

  // 상태: landing → selecting_city → selecting_district → result
  let phase = $state('landing')
  let selectedCity = $state('')
  let selectedDistrict = $state('')

  // URL 파라미터로 바로 결과 진입
  function checkUrlParams() {
    const params = new URLSearchParams(window.location.search)
    const city = params.get('city')
    const district = params.get('district')
    if (city && district && districtData[city]?.[district]) {
      selectedCity = city
      selectedDistrict = district
      phase = 'result'
    }
  }

  $effect(() => {
    checkUrlParams()
    // 카카오 SDK 초기화
    if (KAKAO_JS_KEY && window.Kakao && !window.Kakao.isInitialized()) {
      window.Kakao.init(KAKAO_JS_KEY)
    }
  })

  function startSelection() {
    phase = 'selecting_city'
  }

  function selectCity(city) {
    selectedCity = city
    phase = 'selecting_district'
  }

  function selectDistrict(district) {
    selectedDistrict = district
    phase = 'result'
    const url = new URL(window.location)
    url.searchParams.set('city', selectedCity)
    url.searchParams.set('district', district)
    history.replaceState({}, '', url)
  }

  function reset() {
    selectedCity = ''
    selectedDistrict = ''
    phase = 'landing'
    const url = new URL(window.location)
    url.searchParams.delete('city')
    url.searchParams.delete('district')
    history.replaceState({}, '', url)
  }

  function goBackToCity() {
    selectedCity = ''
    phase = 'selecting_city'
  }

  let cities = Object.keys(districtData).sort()
  let districts = $derived(
    selectedCity ? Object.keys(districtData[selectedCity]).sort() : []
  )
  let currentData = $derived(
    selectedCity && selectedDistrict
      ? districtData[selectedCity][selectedDistrict]
      : null
  )
</script>

<main>
  {#if phase === 'landing'}
    <section class="landing fade-in">
      <div class="landing-emoji">&#x2694;&#xFE0F;</div>
      <h1>동네전쟁</h1>
      <p class="landing-desc">
        우리 동네에는 치킨집이 몇 개?<br />
        카페는? 편의점은?<br />
        지금 바로 확인해보세요!
      </p>
      <button class="btn btn-primary" onclick={startSelection}>
        내 동네 검색하기
      </button>
    </section>

  {:else if phase === 'selecting_city'}
    <section class="selector fade-in">
      <h2>시/도를 선택하세요</h2>
      <div class="district-grid">
        {#each cities as city}
          <button class="district-btn" onclick={() => selectCity(city)}>
            {city.replace(/특별시|광역시|특별자치시|특별자치도/, '')}
          </button>
        {/each}
      </div>
      <button class="btn btn-ghost" onclick={reset}>
        ← 처음으로
      </button>
    </section>

  {:else if phase === 'selecting_district'}
    <section class="selector fade-in">
      <h2>{selectedCity}</h2>
      <p class="selector-sub">구/군을 선택하세요</p>
      <div class="district-grid">
        {#each districts as district}
          <button class="district-btn" onclick={() => selectDistrict(district)}>
            {district}
          </button>
        {/each}
      </div>
      <button class="btn btn-ghost" onclick={goBackToCity}>
        ← 시/도 다시 선택
      </button>
    </section>

  {:else if phase === 'result' && currentData}
    <section class="result fade-in">
      <p class="result-location">{selectedCity} {selectedDistrict}</p>
      <p class="result-sub">에는 이만큼의 가게가 있어요</p>
      <Card city={selectedCity} district={selectedDistrict} data={currentData} />
      <div class="result-actions">
        <Share city={selectedCity} district={selectedDistrict} />
        <button class="btn btn-ghost" onclick={reset}>
          다른 동네 검색하기
        </button>
      </div>
    </section>
  {/if}
</main>

<style>
  main {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 0 20px;
  }

  .landing {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    padding: 40px 0;
  }

  .landing-emoji {
    font-size: 64px;
    line-height: 1;
  }

  h1 {
    font-size: 36px;
    font-weight: 800;
    letter-spacing: -1px;
    margin: 0;
  }

  .landing-desc {
    font-size: 17px;
    color: var(--text-sub);
    text-align: center;
    line-height: 1.6;
    margin-bottom: 12px;
  }

  .selector {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 32px 0;
  }

  .selector h2 {
    font-size: 22px;
    font-weight: 700;
  }

  .selector-sub {
    color: var(--text-sub);
    font-size: 15px;
    margin-top: -8px;
  }

  .result {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 32px 0;
    gap: 4px;
  }

  .result-location {
    font-size: 20px;
    font-weight: 700;
  }

  .result-sub {
    font-size: 15px;
    color: var(--text-sub);
    margin-bottom: 20px;
  }

  .result-actions {
    width: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    margin-top: 16px;
  }
</style>
