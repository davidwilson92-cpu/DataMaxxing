const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

test('recent social links reject executable and credential-bearing URLs',()=>{
  const source=fs.readFileSync('nova/static/studio.js','utf8').split('\n')[0];
  const context=vm.createContext({URL});vm.runInContext(source,context);
  for(const url of ['javascript:alert(1)','data:text/html,test','//evil.test','http://example.test','https://name:secret@example.test']){
    assert.equal(context.safeRecentUrl(url),'');
  }
  assert.equal(context.safeRecentUrl('https://www.instagram.com/p/example/'),'https://www.instagram.com/p/example/');
});
