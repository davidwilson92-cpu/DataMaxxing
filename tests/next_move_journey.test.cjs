const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
function setup(){
 const nodes=new Map();const node=id=>{if(!nodes.has(id))nodes.set(id,{value:'',textContent:'',innerHTML:'',hidden:false,open:false,disabled:false,focus(){},showModal(){this.open=true},addEventListener(){},setAttribute(){}});return nodes.get(id);};
 const calls=[],navigations=[];let busy=false;
 const c=vm.createContext({document:{getElementById:node,querySelector:()=>null,querySelectorAll:()=>[]},headers:{},esc:x=>String(x||''),platformName:x=>x,console,location:{assign:x=>{assert.equal(busy,false,'Clear busy state before navigation to avoid the unsaved-work warning');navigations.push(x)}},window:{zovaWorkspaceUrl:x=>x+'&workspace=7'},sendingMessage:false,mediaUploading:false,studioLoading:false,workspaceEpoch:1,saveDraftNow:async()=>{},studioBusy:value=>{busy=value}});
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
 node('strategy_goal').value='My unfinished edit';calls.length=0;await c.openNextMove();assert.equal(node('strategy_goal').value,'My unfinished edit');assert.equal(calls.filter(x=>x.endsWith('/recommend')).length,0);assert.ok(!calls.some(x=>x.includes('series')));
 ready=false;fail=true;await c.openNextMove();assert.match(node('strategyStatus').textContent,/Try again/);assert.equal(node('recommendButton').hidden,false);
 c.saveDraftNow=async()=>{throw Error('Save failed');};calls.length=0;await vm.runInContext('draftNextMove(9,{})',c);assert.equal(calls.length,0);assert.equal(navigations.length,0);assert.match(node('strategyStatus').textContent,/Save failed/);
 // Opening saved work must not call the AI-generating endpoint or require new AI consent.
 await vm.runInContext('draftNextMove(9,{},41)',c);assert.equal(navigations.length,0);assert.match(node('strategyStatus').textContent,/Save failed/);
 c.saveDraftNow=async()=>{};c.api=async()=>{throw Error('No AI request allowed');};
 await vm.runInContext('draftNextMove(9,{},41)',c);assert.deepEqual(navigations,['/studio?draft=41&workspace=7']);
 assert.match(c.nextMoveCard({...idea,draft_id:41}),/draftNextMove\(9,this,41\)/);
 navigations.length=0;await c.openLinkedDraft('/api/series/occurrences/12/draft',{},'44');assert.deepEqual(navigations,['/studio?draft=44&workspace=7']);
 c.api=async()=>[{id:2,revision:1,status:'active',spec:{frequency:'weekly',mode:'fresh',timezone:'Europe/London'},occurrences:[{id:12,draft_id:44,due_at:'2026-11-01T12:00:00Z',status:'draft'}]}];
 await c.loadSeries();assert.match(node('seriesList').innerHTML,/openLinkedDraft\('\/api\/series\/occurrences\/12\/draft',this,44\)/);
 navigations.length=0;c.saveDraftNow=async()=>{c.workspaceEpoch++;};await vm.runInContext('draftNextMove(9,{},41)',c);assert.equal(navigations.length,0);
 c.saveDraftNow=async()=>{};c.api=async()=>({draft_id:42});await vm.runInContext('draftNextMove(9,{})',c);assert.deepEqual(navigations,['/studio?draft=42&workspace=7']);
 navigations.length=0;c.api=async()=>{c.workspaceEpoch++;return {draft_id:43};};await vm.runInContext('draftNextMove(9,{})',c);assert.equal(navigations.length,0);assert.match(node('strategyStatus').textContent,/current chat is unchanged/);
 c.api=async()=>({items:[{...idea,id:1,kind:'review',brief:'Read recent questions'},idea]});await c.loadNextMoves();assert.match(node('strategyActions').innerHTML,/Show how you make a mug/);assert.doesNotMatch(node('strategyActions').innerHTML,/Read recent questions/);assert.match(node('strategyActions').innerHTML,/1 of 2/);
 c.changeMove(1);assert.match(node('strategyActions').innerHTML,/Read recent questions/);assert.doesNotMatch(node('strategyActions').innerHTML,/Made for your plan|Quick check|Behind the idea|You’ll need|more ideas/);assert.match(node('strategyActions').innerHTML,/2 of 2/);
 c.changeMove(1);assert.match(node('strategyActions').innerHTML,/1 of 2/);c.changeMove(-1);assert.match(node('strategyActions').innerHTML,/2 of 2/);
 assert.equal(c.moveReason('Help beginners book (strategy: reduce friction).'),'Help beginners book.');const card=c.nextMoveCard(idea);assert.ok(!card.includes('Reason (optional)'));assert.match(card,/Change this idea/);assert.doesNotMatch(card,/Remind me|More options/);c.setPlanningView(false);assert.equal(node("nextMoveSettings").hidden,true);assert.equal(node("strategyActions").hidden,false);c.setPlanningView(true);assert.equal(node("nextMoveSettings").hidden,false);assert.equal(node("strategyActions").hidden,true);
 let remaining=[idea,{...idea,id:10}],feedbackCalls=[],generated=0;
 c.api=async(url,options)=>{if(url.includes('/feedback')){feedbackCalls.push(JSON.parse(options.body));remaining.shift();return {};}
 if(url==='/api/strategy/actions')return {items:remaining};
 if(url==='/api/strategy/recommend'){generated++;remaining=[{...idea,id:11}];return {};}
 throw Error(url);};
 await c.actionFeedback(9,'dismissed',{});assert.equal(feedbackCalls[0].reason,'');assert.equal(generated,0);assert.equal(remaining[0].id,10);
 await c.actionFeedback(10,'dismissed',{});assert.equal(generated,1);assert.equal(remaining[0].id,11);
 c.api=async()=>{throw Error('Feedback not saved');};const before=node('strategyActions').innerHTML;await c.actionFeedback(11,'dismissed',{});assert.equal(node('strategyActions').innerHTML,before);assert.match(node('strategyStatus').textContent,/Feedback not saved/);
 c.api=async(url,opts)=>{if(url.includes('/feedback')){feedbackCalls.push(JSON.parse(opts.body));return {};}return {items:[]};};
 node('moveReminder11').value='';await c.remindMove(11,null,{});assert.match(node('strategyStatus').textContent,/future date/);
 await c.remindMove(11,7,{});assert.equal(feedbackCalls.at(-1).status,'snoozed');assert.ok(new Date(feedbackCalls.at(-1).remind_at)>new Date());assert.match(node('strategyStatus').textContent,/Nothing is scheduled/);
 node('moveFeedback11').value='Less filming';let refined=false;c.api=async(url,opts)=>{if(url.includes('/feedback')){assert.equal(JSON.parse(opts.body).reason,'Less filming');return {}; }if(url.endsWith('/recommend')){refined=true;return {};}return {items:[idea]};};await c.refineMove(11,{});assert.ok(refined);
 console.log('Next move journey: automatic ideas, no repeated generation, retry, failed save, workspace link and late response passed.');
})().catch(e=>{console.error(e);process.exitCode=1;});
