<script>
  import districtData from './data/district_counts.json'
  import Card from './lib/Card.svelte'
  import Share from './lib/Share.svelte'

  const KAKAO_JS_KEY = '' // developers.kakao.com에서 발급받은 JavaScript 키

  // 상태: landing → selecting_city → selecting_district → selecting_dong → result
  let phase = $state('landing')
  let selectedCity = $state('')
  let selectedDistrict = $state('')
  let selectedDong = $state('')

  // URL 파라미터로 바로 결과 진입
  function checkUrlParams() {
    const params = new URLSearchParams(window.location.search)
    const city = params.get('city')
    const district = params.get('district')
    const dong = params.get('dong')
    if (city && district && dong && districtData[city]?.[district]?.[dong]) {
      selectedCity = city
      selectedDistrict = district
      selectedDong = dong
      phase = 'result'
    } else if (city && district && districtData[city]?.[district]) {
      // dong 없이 시군구까지만 → 시군구 _total 표시
      selectedCity = city
      selectedDistrict = district
      selectedDong = '_total'
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
    phase = 'selecting_dong'
  }

  function selectDong(dong) {
    selectedDong = dong
    phase = 'result'
    const url = new URL(window.location)
    url.searchParams.set('city', selectedCity)
    url.searchParams.set('district', selectedDistrict)
    url.searchParams.set('dong', dong)
    history.replaceState({}, '', url)
  }

  function reset() {
    selectedCity = ''
    selectedDistrict = ''
    selectedDong = ''
    phase = 'landing'
    const url = new URL(window.location)
    url.searchParams.delete('city')
    url.searchParams.delete('district')
    url.searchParams.delete('dong')
    history.replaceState({}, '', url)
  }

  function goBackToCity() {
    selectedCity = ''
    selectedDistrict = ''
    phase = 'selecting_city'
  }

  function goBackToDistrict() {
    selectedDong = ''
    phase = 'selecting_district'
  }

  function goBackToDong() {
    selectedDong = ''
    phase = 'selecting_dong'
  }

  let cities = Object.keys(districtData).sort()
  let districts = $derived(
    selectedCity ? Object.keys(districtData[selectedCity]).sort() : []
  )
  let dongs = $derived(
    selectedCity && selectedDistrict
      ? Object.keys(districtData[selectedCity][selectedDistrict])
          .filter(d => d !== '_total')
          .sort()
      : []
  )
  let displayName = $derived(
    selectedDong === '_total'
      ? `${selectedCity} ${selectedDistrict}`
      : `${selectedDistrict} ${selectedDong}`
  )
  let currentData = $derived(
    selectedCity && selectedDistrict && selectedDong
      ? districtData[selectedCity][selectedDistrict][selectedDong]
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

  {:else if phase === 'selecting_dong'}
    <section class="selector fade-in">
      <h2>{selectedCity} {selectedDistrict}</h2>
      <p class="selector-sub">동/읍/면을 선택하세요</p>
      <button class="district-btn district-btn--total" onclick={() => selectDong('_total')}>
        {selectedDistrict} 전체
      </button>
      <div class="district-grid">
        {#each dongs as dong}
          <button class="district-btn" onclick={() => selectDong(dong)}>
            {dong}
          </button>
        {/each}
      </div>
      <button class="btn btn-ghost" onclick={goBackToDistrict}>
        ← 구/군 다시 선택
      </button>
    </section>

  {:else if phase === 'result' && currentData}
    <section class="result fade-in">
      <p class="result-location">{displayName}</p>
      <p class="result-sub">에는 이만큼의 가게가 있어요</p>
      <Card city={selectedCity} district={displayName} data={currentData} />
      <div class="result-actions">
        <Share city={selectedCity} district={displayName} dong={selectedDong} />
        <button class="btn btn-ghost" onclick={goBackToDong}>
          ← 다른 동 선택하기
        </button>
        <button class="btn btn-ghost" onclick={reset}>
          처음부터 다시
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
