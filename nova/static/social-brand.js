/* Locally hosted platform marks; see docs/INSTAGRAM_ASSET.md. */
const platformAssets = JSON.parse(document.currentScript?.dataset?.icons || '{}');
window.zovaInstagramIcon = () => '<span class="instagram-glyph" role="img" aria-label="Instagram" title="Instagram"></span>';
window.zovaPlatformLabel = platform => {
  if (platform === 'instagram') return window.zovaInstagramIcon();
  const name = {x:'X', facebook:'Facebook', tiktok:'TikTok'}[platform];
  if (!name) return 'Social';
  const source = platformAssets[platform] || `/static/${platform}-brand.svg`;
  return `<img class="platform-brand-icon" src="${source}" alt="${name}" title="${name}" width="24" height="24">`;
};
