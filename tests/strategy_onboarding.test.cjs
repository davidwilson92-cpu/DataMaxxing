const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const nodes = new Map();
function node(id) { if (!nodes.has(id)) nodes.set(id, {value:'',textContent:'',innerHTML:'',hidden:false,open:true,focus(){this.focused=true},addEventListener(){}}); return nodes.get(id); }
let calls=0, payload, reject=false;
const context = vm.createContext({document:{getElementById:node,querySelectorAll:()=>[]},headers:{},esc:x=>x,console,api:async(url,options)=>{calls++;payload=JSON.parse(options.body);if(reject)throw Error('Save unavailable');return {revision:2,proposal:{strategy:{goal:'Fill Saturday classes',themes:'Local pottery'},assumptions:[]}}}});
vm.runInContext(fs.readFileSync('nova/static/strategy.js','utf8'),context);
(async()=>{
 node('strategyBrief').value='';await context.proposeStrategy({});assert.equal(calls,0);assert.match(node('strategyStatus').textContent,/Add a short goal/);
 node('strategyBrief').value='Fill Saturday classes';node('strategyQuickAudience').value='Local beginners';node('strategyQuickTime').value='30 minutes weekly';
 reject=true;await context.proposeStrategy({});assert.equal(node('strategyBrief').value,'Fill Saturday classes');assert.equal(node('strategyQuickAudience').value,'Local beginners');assert.equal(node('strategyQuickStart').open,true);
 reject=false;await context.proposeStrategy({});assert.match(payload.brief,/Audience: Local beginners/);assert.match(payload.brief,/Time and resources: 30 minutes weekly/);assert.equal(node('strategyQuickStart').open,false);assert.equal(node('strategyForm').hidden,false);assert.equal(node('strategyReviewHeading').focused,true);assert.equal(node('strategySearchPreview').textContent,'Local pottery');
 node('strategyBrief').value='x'.repeat(20000);const prior=calls;await context.proposeStrategy({});assert.equal(calls,prior);assert.equal(node('strategyBrief').value.length,20000);assert.match(node('strategyStatus').textContent,/shorten/);
 context.fillStrategy({goal:'Saved goal',audience:'Saved audience',resources:'Saved time',voice:'Saved voice',themes:'Saved topic',avoid:'Do not change'});assert.equal(node('strategy_voice').value,'Saved voice');assert.equal(node('strategy_avoid').value,'Do not change');assert.equal(node('strategySearchPreview').textContent,'Saved topic');
 vm.runInContext('hasConfirmedStrategy=true',context);context.platformName=x=>x;
 context.api=async()=>({source_note:'Evergreen',performance_note:'Recent snapshot only',items:[{id:1,title:'Review questions',reason:'Learn what people ask',brief:'Open your social account and review recent questions.',platform:'instagram',kind:'review',effort:'5 minutes'}]});
 await context.loadNextMoves();assert.match(node('strategyActions').innerHTML,/Mark reviewed/);assert.doesNotMatch(node('strategyActions').innerHTML,/draftNextMove/);assert.match(node('strategyActions').innerHTML,/Open your social account/);assert.match(node('strategyPerformanceNote').innerHTML,/href="\/analytics"/);
 context.api=async()=>({source_note:'Evergreen',items:[{id:2,title:'Legacy draft',reason:'A saved suggestion',platform:'instagram',effort:'5 minutes'}]});await context.loadNextMoves();assert.match(node('strategyActions').innerHTML,/draftNextMove/);assert.equal(node('strategyPerformanceNote').hidden,true);
 node('strategyBrief').value='My existing idea';context.chooseStrategyGoal('Build awareness');assert.equal(node('strategyBrief').value,'My existing idea\nBuild awareness');context.chooseStrategyGoal('Build awareness');assert.equal(node('strategyBrief').value,'My existing idea\nBuild awareness');node('strategyBrief').value='x'.repeat(20000);context.chooseStrategyGoal('Get enquiries');assert.equal(node('strategyBrief').value.length,20000);context.strategyStepHint('proposal');assert.match(node('strategyStepHint').textContent,/confirm/);context.strategyStepHint('confirmed');assert.match(node('strategyStepHint').textContent,/confirmed strategy/);console.log('Strategy onboarding: 9 behavior groups passed.');
})().catch(error=>{console.error(error);process.exitCode=1});
