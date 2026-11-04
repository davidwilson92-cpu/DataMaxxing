// Reuse the exact locally hosted web marks in the native asset catalogue.
// Run with the workspace's installed sharp package on NODE_PATH.
const fs = require('node:fs');
const path = require('node:path');
const sharp = require('sharp');
(async () => {
  const root = path.resolve(__dirname, '..');
  for (const platform of ['x', 'instagram', 'facebook', 'tiktok']) {
    const directory = path.join(root, 'ios/Zova/Assets.xcassets', `Platform-${platform}.imageset`);
    fs.mkdirSync(directory, {recursive: true});
    let source;
    if (platform === 'instagram') {
      // Same centered 400%-wide crop as the mobile web CSS, without changing art.
      source = sharp(path.join(root, 'nova/static/instagram-official.png')).extract({left: 427, top: 172, width: 285, height: 285});
    } else source = sharp(path.join(root, `nova/static/${platform}-brand.svg`), {density: 288});
    await source.resize(96, 96).png().toFile(path.join(directory, 'mark.png'));
    fs.writeFileSync(path.join(directory, 'Contents.json'), JSON.stringify({images:[{filename:'mark.png',idiom:'universal'}],info:{author:'xcode',version:1}}, null, 2)+'\n');
  }
})();
