const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
function setup(){
 const elements=new Map(),panels=[{hidden:false},{hidden:false},{hidden:false}],requests=[];
 const get=id=>{if(!elements.has(id))elements.set(id,{innerHTML:'',textContent:'',hidden:false,disabled:false,value:'7',addEventListener(){}});return elements.get(id);};
 const context={URL,console,document:{getElementById:get,querySelector:()=>get('questionButton'),querySelectorAll:s=>s==='.analytics-split,.content-panel,.analytics-ask'?panels:[]},window:{zovaPlatformLabel:p=>p},fetch:(url,options)=>new Promise(resolve=>requests.push({url,options,resolve}))};
 vm.createContext(context);vm.runInContext(fs.readFileSync('nova/static/analytics.js','utf8'),context);
 return {context,get,panels,requests};
}
const ok=data=>({ok:true,json:async()=>data});
const sample={platforms:{x:{connected:true}},summary:{likes:5},recommendations:[],top_posts:[],fetched_at:'2026-10-19T10:00:00Z'};
test('failed refresh hides previous results and old answers cannot land in a new window',async()=>{
 const t=setup();t.requests[0].resolve(ok(sample));await new Promise(setImmediate);
 assert.equal(t.panels[0].hidden,false);
 const answer=t.context.askAnalytics('likes');
 t.get('analyticsWindow').value='30';const refresh=t.context.loadAnalytics();
 t.requests[1].resolve(ok({answer:'Old seven-day answer'}));await answer;
 assert.equal(t.get('analyticsAnswer').hidden,true);
 assert.notEqual(t.get('analyticsAnswer').textContent,'Old seven-day answer');
 t.requests[2].resolve({ok:false,json:async()=>({detail:'Offline'})});await refresh;
 assert.equal(t.panels[0].hidden,true);
 assert.match(t.get('analyticsKpis').innerHTML,/Offline/);
});
test('question includes chosen window and untrusted links cannot execute',async()=>{
 const t=setup();t.requests[0].resolve(ok(sample));await new Promise(setImmediate);
 t.get('analyticsWindow').value='30';const answer=t.context.askAnalytics('views');
 assert.equal(JSON.parse(t.requests[1].options.body).days,30);
 t.requests[1].resolve(ok({answer:'Current result'}));await answer;
 t.context.renderPosts([{platform:'x',url:'javascript:alert(1)',image_url:'data:text/html,unsafe',text:'<script>bad</script>'}]);
 assert.doesNotMatch(t.get('topPosts').innerHTML,/javascript:|data:text|<script>/);
 assert.match(t.get('topPosts').innerHTML,/&lt;script&gt;/);
 t.context.renderKpis({impressions:null,comments:null,followers:null,posts:null});
 assert.match(t.get('analyticsKpis').innerHTML,/Combined totals are incomplete/);
 t.context.renderKpis({posts:0});assert.match(t.get('analyticsKpis').innerHTML,/>0</);
});
