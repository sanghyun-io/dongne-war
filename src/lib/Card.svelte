<script>
  import { generateFunFact } from './funFacts.js'

  let { city, district, data } = $props()

  const CATEGORIES = [
    { key: 'chicken', emoji: '\u{1F357}', label: '치킨집', color: 'var(--c-chicken)' },
    { key: 'cafe', emoji: '\u2615', label: '카페', color: 'var(--c-cafe)' },
    { key: 'convenience', emoji: '\u{1F3EA}', label: '편의점', color: 'var(--c-convenience)' },
    { key: 'realestate', emoji: '\u{1F3E0}', label: '부동산', color: 'var(--c-realestate)' },
    { key: 'pharmacy', emoji: '\u{1F48A}', label: '약국', color: 'var(--c-pharmacy)' },
    { key: 'pcroom', emoji: '\u{1F5A5}\u{FE0F}', label: 'PC방', color: 'var(--c-pcroom)' },
  ]

  let maxCount = $derived(Math.max(...CATEGORIES.map(c => data[c.key] || 0), 1))

  let topCategory = $derived(() => {
    let top = CATEGORIES[0]
    for (const cat of CATEGORIES) {
      if ((data[cat.key] || 0) > (data[top.key] || 0)) top = cat
    }
    return top
  })

  let funFact = $derived(generateFunFact(data))
</script>

<div class="card" id="capture-card">
  <div class="card-header">
    <p class="card-location">{city} {district}</p>
    <p class="card-subtitle">우리 동네 업종 대전</p>
  </div>

  <div class="card-bars">
    {#each CATEGORIES as cat}
      {@const count = data[cat.key] || 0}
      {@const pct = (count / maxCount) * 100}
      <div class="bar-row">
        <span class="bar-emoji">{cat.emoji}</span>
        <span class="bar-label">{cat.label}</span>
        <div class="bar-track">
          <div
            class="bar-fill"
            style="width: {pct}%; background: {cat.color};"
          ></div>
        </div>
        <span class="bar-count" style="color: {cat.color};">
          {count.toLocaleString()}
        </span>
      </div>
    {/each}
  </div>

  <div class="card-highlight">
    <span class="highlight-badge">
      {topCategory().emoji} 1위: {topCategory().label}
      {(data[topCategory().key] || 0).toLocaleString()}개
    </span>
  </div>

  {#if funFact}
    <p class="card-funfact">"{funFact}"</p>
  {/if}

  <p class="card-watermark">dongne-war.gamja.top</p>
</div>

<style>
  .card {
    width: 100%;
    background: var(--bg-card);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 28px 20px 20px;
    animation: scaleIn 0.4s ease-out;
  }

  .card-header {
    text-align: center;
    margin-bottom: 20px;
  }

  .card-location {
    font-size: 20px;
    font-weight: 800;
    letter-spacing: -0.5px;
  }

  .card-subtitle {
    font-size: 13px;
    color: var(--text-sub);
    margin-top: 2px;
  }

  .card-bars {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .card-highlight {
    text-align: center;
    margin-top: 16px;
  }

  .highlight-badge {
    display: inline-block;
    padding: 8px 16px;
    background: #fef3c7;
    border-radius: 20px;
    font-size: 14px;
    font-weight: 700;
  }

  .card-funfact {
    text-align: center;
    font-size: 14px;
    color: var(--text-sub);
    margin-top: 12px;
    font-style: italic;
  }

  .card-watermark {
    text-align: center;
    font-size: 11px;
    color: #d6d3d1;
    margin-top: 16px;
    letter-spacing: 0.5px;
  }
</style>
