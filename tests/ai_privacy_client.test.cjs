const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const tick=()=>new Promise(setImmediate);
function setup({saveFails=false}={}){
 const listeners={},events=[],controls={};
 for(const name of ['[role="status"]','[data-ai-allow]','[data-ai-cancel]'])controls[name]={textContent:'',disabled:false,focus(){}};
 const dialog={open:false,querySelector:s=>controls[s],addEventListener:(name,fn)=>listeners[name]=fn,removeEventListener:name=>delete listeners[name],showModal(){this.open=true;},close(){this.open=false;listeners.close?.();}};
 const original=async(url,options={})=>{
   events.push({url,options});
   if(url==='/api/privacy/ai')return new Response(JSON.stringify(options.method?{allowed:true,version:'2026-10-19'}:{allowed:false,required:true,version:'2026-10-19'}),{status:saveFails&&options.method?500:200});
   return new Response('{}');
 };
 const context={URL,Request,Response,location:{href:'https://zova.example/studio',origin:'https://zova.example'},window:{fetch:original},document:{getElementById:id=>id==='aiPrivacyDialog'?dialog:null,addEventListener(){}}};
 vm.createContext(context);vm.runInContext(fs.readFileSync('nova/static/ai-privacy.js','utf8'),context);
 return {...context,controls,dialog,events};
}
test('cancel sends no idea to the provider route and non-AI work is still usable',async()=>{
 const t=setup();const sent=t.window.fetch('/api/conversation/plan',{method:'POST',body:'private idea'});
 await tick();assert.equal(t.dialog.open,true);
 t.controls['[data-ai-cancel]'].onclick();assert.equal((await sent).status,403);
 assert.equal(t.events.filter(e=>e.url==='/api/conversation/plan').length,0);
 await t.window.fetch('/api/drafts',{method:'POST'});
 assert.equal(t.events.at(-1).url,'/api/drafts');
});
test('explicit saved choice precedes the original request, concurrent requests share one choice',async()=>{
 const t=setup();const a=t.window.fetch('/api/conversation/plan',{method:'POST'}),b=t.window.fetch('/api/ai/generate',{method:'POST'});
 await tick();assert.equal(t.events.length,1);
 await t.controls['[data-ai-allow]'].onclick();await Promise.all([a,b]);
 assert.deepEqual(t.events.slice(0,2).map(e=>e.url),['/api/privacy/ai','/api/privacy/ai']);
 assert.equal(JSON.parse(t.events[1].options.body).allowed,true);
 assert.equal(t.events.length,4);assert.equal(t.dialog.open,false);
});
test('a failed consent save never releases the waiting AI request',async()=>{
 const t=setup({saveFails:true});const sent=t.window.fetch('/api/strategy/recommend',{method:'POST'});
 await tick();await t.controls['[data-ai-allow]'].onclick();
 assert.equal(t.dialog.open,true);assert.equal(t.controls['[data-ai-allow]'].disabled,false);
 assert.match(t.controls['[role="status"]'].textContent,/could not be saved/);
 assert.equal(t.events.length,2);
 t.controls['[data-ai-cancel]'].onclick();assert.equal((await sent).status,403);
});
