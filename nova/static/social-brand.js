/* Locally hosted platform marks; see docs/INSTAGRAM_ASSET.md. */
window.zovaInstagramIcon=()=>'<span class="instagram-glyph" role="img" aria-label="Instagram" title="Instagram"></span>';
window.zovaPlatformLabel=p=>{const name={x:'X',facebook:'Facebook',tiktok:'TikTok'}[p];return p==='instagram'?window.zovaInstagramIcon():name?`<img class="platform-brand-icon" src="/static/${p}-brand.svg" alt="${name}" title="${name}" width="24" height="24">`:'Social';};
