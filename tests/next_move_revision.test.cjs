const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const nodes=new Map();
function node(id){if(!nodes.has(id))nodes.set(id,{value:'',textContent:'',innerHTML:'',hidden:false,open:false,handlers:{},focus(){this.focused=true},showModal(){this.open=true},addEventListener(name,fn){this.handlers[name]=fn},setAttribute(){}});return nodes.get(id);}
const platforms=[{value:'instagram',checked:true}];
const context=vm.createContext({window:{},document:{getElementById:node,querySelector:()=>null,querySelectorAll:selector=>selector.includes(':checked')?platforms:[]},headers:{},esc:x=>String(x||''),platformName:x=>x,console});
vm.runInContext(fs.readFileSync(process.argv[2]||'nova/static/strategy.js','utf8'),context);
const old={id:1,title:'Gym workout',platform:'instagram',reason:'Help gym beginners',kind:'draft'},fresh={...old,id:2,title:'Restaurant lunch'};
const plan={goal:'Restaurant bookings',platforms:['instagram'],description:'I run a restaurant, not a gym.'};
(async()=>{
 vm.runInContext('strategyRevision=1;hasConfirmedStrategy=true;strategyLoaded=true',context);
 context.api=async()=>({revision:1,items:[old]});await context.loadNextMoves();
 assert.match(node('strategyActions').innerHTML,/Gym workout/);
 // Reopening must remove old interactive DOM immediately, not after either GET.
 let resolvePlan,resolveActions;
 context.api=url=>new Promise(resolve=>{if(url==='/api/strategy')resolvePlan=resolve;else resolveActions=resolve;});
 const opening=context.openNextMove();
 assert.doesNotMatch(node('strategyActions').innerHTML,/Gym workout|next-move-featured/);
 resolvePlan({revision:1,confirmed:{goal:'Gym',platforms:['instagram']},proposal:{},defaults:{}});
 await new Promise(setImmediate);
 assert.equal(typeof resolveActions,'function');
 assert.doesNotMatch(node('strategyActions').innerHTML,/Gym workout|next-move-featured/);
 resolveActions({revision:1,items:[old]});await opening;
 assert.match(node('strategyActions').innerHTML,/Gym workout/);
 // The saved revision changes, then the next request fails: never leave the previous business's card on screen.
 context.api=async url=>{if(url==='/api/strategy')return {revision:2,confirmed:plan,proposal:{},defaults:{}};throw Error('Connection interrupted. Retry.');};
 await context.openNextMove();
 assert.doesNotMatch(node('strategyActions').innerHTML,/Gym workout/);
 assert.match(node('strategyStatus').textContent,/Connection interrupted/);
 // Late action responses from the previous modal cannot replace the newer strategy view.
 let resolveOld;
 context.api=()=>new Promise(resolve=>{resolveOld=resolve});
 const pending=context.loadNextMoves();
 context.api=async url=>({revision:3,confirmed:plan,proposal:{},defaults:{}});
 await context.openNextMove(true);
 resolveOld({revision:2,items:[old]});await pending;
 assert.doesNotMatch(node('strategyActions').innerHTML,/Gym workout/);
 assert.equal(node('nextMoveSettings').hidden,false);
 // Closing while a proposal is being generated cannot overwrite a later open view.
 let resolveProposal;
 node('strategyBrief').value='New restaurant strategy';
 context.api=()=>new Promise(resolve=>{resolveProposal=resolve});
 const proposalPending=context.proposeStrategy({});
 node('strategyPanel').handlers.close();
 context.api=async()=>({revision:4,confirmed:plan,proposal:{},defaults:{}});
 await context.openNextMove(true);
 resolveProposal({revision:4,proposal:{strategy:{goal:'Old gym'},assumptions:[]}});await proposalPending;
 assert.equal(node('strategy_goal').value,'Restaurant bookings');
 // Saving is distinct from generating: a saved strategy is not reported as failed because ideas are unavailable.
 let calls=[];
 node('strategyActions').innerHTML='<article class="next-move-featured">Gym workout</article>';
 context.api=async(url,options)=>{calls.push(url);return {revision:5,confirmed:{...plan,...JSON.parse(options.body).strategy}}};
 await context.confirmStrategy({preventDefault(){},submitter:{}});
 assert.doesNotMatch(node('strategyActions').innerHTML,/Gym workout|next-move-featured/);
 assert.deepEqual(calls,['/api/strategy/confirm']);
 assert.match(node('strategyStatus').textContent,/Strategy saved/);
 assert.equal(node('strategyNextMoveButton').hidden,false);
 assert.equal(node('saveStrategyButton').hidden,true);
 // No generic “couldn't load ideas” replaces the actionable server error.
 context.api=async()=>{throw Error('Enable AI assistance in Account to find ideas.');};
 await context.refreshStrategyActions({});
 assert.equal(node('strategyStatus').textContent,'Enable AI assistance in Account to find ideas.');
 // A newer server revision also cannot be rendered against this tab's older strategy.
 context.api=async()=>({revision:6,items:[fresh]});
 await assert.rejects(context.loadNextMoves(),/strategy changed/);
 assert.doesNotMatch(node('strategyActions').innerHTML,/Restaurant lunch/);
 console.log('Next move revision changes, failed fetch, late modal/proposal replies, separate save and exact retry errors passed.');
})().catch(error=>{console.error(error);process.exitCode=1});
