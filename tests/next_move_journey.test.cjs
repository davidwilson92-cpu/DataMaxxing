const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
function setup(){
 const nodes=new Map();const node=id=>{if(!nodes.has(id))nodes.set(id,{value:'',textContent:'',innerHTML:'',hidden:false,open:false,disabled:false,focus(){},showModal(){this.open=true},addEventListener(){}});return nodes.get(id);};
 const calls=[],navigations=[];let busy=false;
 const c=vm.createContext({document:{getElementById:node,querySelectorAll:()=>[]},headers:{},esc:x=>String(x||''),platformName:x=>x,console,location:{assign:x=>{assert.equal(busy,false,'Clear busy state before navigation to avoid the unsaved-work warning');navigations.push(x)}},window:{zovaWorkspaceUrl:x=>x+'&workspace=7'},sendingMessage:false,mediaUploading:false,studioLoading:false,workspaceEpoch:1,saveDraftNow:async()=>{},studioBusy:value=>{busy=value}});
 vm.runInContext(fs.readFileSync('nova/static/strategy.js','utf8'),c);
 return {c,node,calls,navigations};
}
const idea={id:9,title:'Show how you make a mug',reason:'Help beginners get started.',platform:'instagram',format:'post',kind:'draft',effort:'5 minutes',needs:''};
(async()=>{
 const {c,node,calls,navigations}=setup();let ready=false,fail=false;
 c.api=async(url)=>{calls.push(url);if(url==='/api/strategy')return {revision:4,confirmed:{goal:'Grow',platforms:['instagram']},proposal:{},defaults:{}};
 if(url==='/api/strategy/actions')return {items:ready?[idea]:[],source_note:'Evergreen'};
 if(url==='/api/strategy/recommend'){if(fail)throw Error('Could not find ideas. Try again.');ready=true;return {};}
 throw Error('Unexpected request '+url);};
 await c.openNextMove();assert.equal(calls.filter(x=>x.endsWith('/recommend')).length,1);assert.match(node('strategyActions').innerHTML,/Draft post/);assert.equal(node('strategyStatus').textContent,'');
 calls.length=0;await c.openNextMove();assert.equal(calls.filter(x=>x.endsWith('/recommend')).length,0);assert.ok(!calls.some(x=>x.includes('series')));
 ready=false;fail=true;await c.openNextMove();assert.match(node('strategyStatus').textContent,/Try again/);assert.equal(node('recommendButton').hidden,false);
 c.saveDraftNow=async()=>{throw Error('Save failed');};calls.length=0;await vm.runInContext('draftNextMove(9,{})',c);assert.equal(calls.length,0);assert.equal(navigations.length,0);assert.match(node('strategyStatus').textContent,/Save failed/);
 c.saveDraftNow=async()=>{};c.api=async()=>({draft_id:42});await vm.runInContext('draftNextMove(9,{})',c);assert.deepEqual(navigations,['/studio?draft=42&workspace=7']);
 navigations.length=0;c.api=async()=>{c.workspaceEpoch++;return {draft_id:43};};await vm.runInContext('draftNextMove(9,{})',c);assert.equal(navigations.length,0);assert.match(node('strategyStatus').textContent,/current chat is unchanged/);
 c.api=async()=>({items:[{...idea,id:1,kind:'review',brief:'Read recent questions'},idea]});await c.loadNextMoves();assert.ok(node('strategyActions').innerHTML.indexOf('Your next post')<node('strategyActions').innerHTML.indexOf('Quick check'));assert.match(node('strategyActions').innerHTML,/1 more idea/);
 console.log('Next move journey: automatic ideas, no repeated generation, retry, failed save, workspace link and late response passed.');
})().catch(e=>{console.error(e);process.exitCode=1;});
