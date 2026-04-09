<script>
  import html2canvas from 'html2canvas-pro'

  let { city, district, dong = '' } = $props()

  async function saveImage() {
    const el = document.getElementById('capture-card')
    if (!el) return
    try {
      const canvas = await html2canvas(el, {
        backgroundColor: '#ffffff',
        scale: 2,
        useCORS: true,
      })
      canvas.toBlob((blob) => {
        if (!blob) return
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `dongne-war-${district}${dong && dong !== '_total' ? '-' + dong : ''}.png`
        a.click()
        URL.revokeObjectURL(url)
      })
    } catch (e) {
      console.error('Image capture failed:', e)
    }
  }

  function buildShareUrl() {
    const url = new URL(window.location.origin)
    url.searchParams.set('city', city)
    url.searchParams.set('district', district)
    if (dong) url.searchParams.set('dong', dong)
    return url.toString()
  }

  function copyLink() {
    navigator.clipboard.writeText(buildShareUrl()).then(() => {
      linkCopied = true
      setTimeout(() => (linkCopied = false), 2000)
    })
  }

  function shareKakao() {
    if (!window.Kakao?.isInitialized()) return
    const shareUrl = buildShareUrl()
    const displayName = dong && dong !== '_total' ? `${district} ${dong}` : district
    window.Kakao.Share.sendDefault({
      objectType: 'feed',
      content: {
        title: `${displayName} 동네전쟁`,
        description: '우리 동네 업종 대전! 치킨집 vs 카페 vs 편의점',
        imageUrl: 'https://dongne-war.gamja.top/og-image.png',
        link: {
          mobileWebUrl: shareUrl,
          webUrl: shareUrl,
        },
      },
      buttons: [
        {
          title: '내 동네도 확인하기',
          link: {
            mobileWebUrl: shareUrl,
            webUrl: shareUrl,
          },
        },
      ],
    })
  }

  let linkCopied = $state(false)
  let kakaoAvailable = $derived(
    typeof window !== 'undefined' && window.Kakao?.isInitialized?.()
  )
</script>

<div class="share-row">
  {#if kakaoAvailable}
    <button class="btn btn-kakao" onclick={shareKakao}>
      카카오톡
    </button>
  {/if}
  <button class="btn btn-secondary" onclick={saveImage}>
    이미지 저장
  </button>
  <button class="btn btn-secondary" onclick={copyLink}>
    {linkCopied ? '복사됨!' : '링크 복사'}
  </button>
</div>

<style>
  .btn-kakao {
    background: #fee500;
    color: #191919;
    border: none;
    font-family: var(--sans);
    font-size: 14px;
    font-weight: 600;
    padding: 12px 16px;
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: transform 0.15s;
  }

  .btn-kakao:active {
    transform: scale(0.97);
  }

  .share-row {
    width: 100%;
  }

  .share-row :global(.btn-secondary) {
    font-size: 14px;
    padding: 12px 16px;
  }
</style>
