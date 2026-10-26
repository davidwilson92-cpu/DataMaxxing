process.env.TZ='Europe/London';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const nodes=new Map(),listeners={};
function node(id){if(!nodes.has(id))nodes.set(id,{innerHTML:'',textContent:'',value:'',hidden:false,attrs:{},addEventListener(type,fn){this[type]=fn;},setAttribute(k,v){this.attrs[k]=v;},focus(){},scrollIntoView(){}});return nodes.get(id);}
let mode='get',calls=0,release,navigation='';
const context=vm.createContext({Date,Intl,Map,Set,Number,JSON,String,URLSearchParams,console,
 window:{location:{search:'',assign:path=>navigation=path},zovaWorkspaceUrl:path=>path+(path.includes('?')?'&':'?')+'workspace=7'},
 confirm:()=>{throw Error('Native JavaScript dialogs must not be used');},
 document:{getElementById:node,querySelectorAll:()=>[],querySelector:()=>node('focused'),addEventListener:(type,fn)=>listeners[type]=fn},
 fetch:async(url,options)=>{if(options?.method){calls++;if(mode==='hold')await new Promise(resolve=>release=resolve);return {ok:false,json:async()=>({detail:'Temporary failure'})};}return {ok:true,json:async()=>[]};}
});
vm.runInContext(fs.readFileSync('nova/static/drafts.js','utf8'),context);
(async()=>{
 await context.loadSchedules();
 assert.match(node('scheduledJobs').innerHTML,/Nothing scheduled this month/);
 assert.equal(node('scheduleZone').textContent,'Times in Europe/London');
 assert.match(node('scheduleCalendar').innerHTML,/data-schedule-day/);
 const bounds=context.scheduleMonthBounds(0,new Date('2026-10-25T12:00:00Z'));
 assert.equal((bounds.end-bounds.start)/3600000,745); // Month includes the autumn clock change.
 assert.throws(()=>context.scheduleLocalInstant('2026-03-29T01:30'),/does not exist/);
 assert.throws(()=>context.scheduleLocalInstant('2026-10-25T01:30'),/occurs twice/);
 assert.equal(context.scheduleLocalInstant('2026-09-29T12:00'),'2026-09-29T11:00:00.000Z');

 vm.runInContext(`scheduleRows=[{id:1,draft_id:8,platform:'instagram',title:'<script>bad</script>',scheduled_at:'2026-09-29T11:00:00Z',status:'unknown'},{id:2,draft_id:9,platform:'x',scheduled_at:'2026-09-30T11:00:00Z',status:'pending'},{id:4,draft_id:9,platform:'x',scheduled_at:'2026-09-30T11:00:00Z',status:'cancelled'}]`,context);
 context.renderAgenda();
 assert.match(node('scheduledJobs').innerHTML,/workspace=7/);
 assert.match(node('scheduledJobs').innerHTML,/Outcome unconfirmed/);
 assert.match(node('scheduledJobs').innerHTML,/Pending at platform/);
 assert.doesNotMatch(node('scheduledJobs').innerHTML,/data-schedule-action|<script>|schedule-row-4/);
 assert.match(node('scheduledJobs').innerHTML,/&lt;script&gt;/);

 vm.runInContext(`scheduleRows=[{id:3,draft_id:12,draft_revision:4,updated_at:'2026-09-01T12:00:00Z',title:'A saved post',platform:'instagram',scheduled_at:'2026-10-01T11:00:00Z',status:'scheduled'}];scheduleExpanded='3-reschedule'`,context);
 context.renderAgenda();
 assert.match(node('scheduledJobs').innerHTML,/value="2026-10-01T12:00"/);
 node('time-3').value='2026-10-02T12:00';mode='hold';const button={disabled:false};
 const first=context.changeSchedule(3,'reschedule',button);await context.changeSchedule(3,'reschedule',button);
 assert.equal(calls,1);release();await first;
 assert.equal(node('time-3').value,'2026-10-02T12:00');assert.match(node('scheduleStatus').textContent,/still here/);assert.equal(button.disabled,false);
 context.renderAgenda();assert.match(node('scheduledJobs').innerHTML,/value="2026-10-02T12:00"/);

 listeners.click({target:{closest:()=>({dataset:{scheduleAction:'cancel',id:'3'}})}});
 assert.match(node('scheduledJobs').innerHTML,/Cancel delivery/);assert.equal(calls,1);
 let mutations=[];
 context.fetch=async(url,options)=>{if(options?.method){mutations.push({url,body:JSON.parse(options.body)});return {ok:true,json:async()=>({status:'cancelled'})};}return {ok:true,json:async()=>[]};};
 await context.changeSchedule(3,'cancel',{disabled:false});
 assert.match(mutations[0].url,/\/api\/schedules\/3\/cancel\?workspace=7/);
 assert.equal(mutations[0].body.expected_updated_at,'2026-09-01T12:00:00Z');
 assert.match(node('scheduleStatus').textContent,/Delivery cancelled/);
 context.showScheduleView('saved');assert.equal(navigation,'/drafts?view=saved&workspace=7');

 vm.runInContext(`scheduleRows=[{id:3,draft_id:12,draft_revision:4,platform:'instagram',scheduled_at:'2026-10-01T11:00:00Z',status:'scheduled'}];scheduleSavedDirty=false`,context);
 context.fetch=async(url,options)=>{mutations.push({url,body:JSON.parse(options.body)});return {ok:true,json:async()=>({draft_id:12,status:'draft'})};};
 await context.changeSchedule(3,'edit',{disabled:false});
 assert.equal(mutations.at(-1).body.revision,4);
 assert.equal(navigation,'/studio?draft=12&workspace=7');

 const focusRequests=[];
 context.fetch=async url=>{focusRequests.push(url);return {ok:true,json:async()=>[{id:51,draft_id:44,title:'A later post',platform:'x',scheduled_at:'2027-02-10T11:00:00Z',status:'scheduled'}]};};
 await context.findSchedule(44);
 assert.match(focusRequests[0],/\/api\/schedules\?draft_id=44&workspace=7/);
 assert.match(focusRequests[1],/from=2027-02-01/);
 assert.match(node('scheduledJobs').innerHTML,/A later post/);
 // Both UK and US hosts must show the focused day; date order follows the device locale.
 assert.match(node('scheduleListTitle').textContent,/\b10\b/);
 assert.match(node('scheduleListTitle').textContent,/February/);

 vm.runInContext(`scheduleHasMore=true;scheduleRows=[]`,context);context.renderAgenda();assert.match(node('scheduledJobs').innerHTML,/latest 100/);
 const pending=[];context.fetch=url=>new Promise(resolve=>pending.push({url,resolve}));
 vm.runInContext('scheduleRequestedMonth=1',context);const older=context.loadSchedules();
 vm.runInContext('scheduleRequestedMonth=2',context);const newer=context.loadSchedules();
 pending[1].resolve({ok:true,headers:{get:()=> 'true'},json:async()=>[]});await newer;
 const rendered=node('scheduledJobs').innerHTML;
 pending[0].resolve({ok:true,headers:{get:()=> 'false'},json:async()=>[{id:99,draft_id:99,platform:'x',status:'unknown',scheduled_at:new Date().toISOString()}]});await older;
 assert.equal(node('scheduledJobs').innerHTML,rendered);
 assert.match(rendered,/incomplete/);
 console.log('Schedule: calendar, DST, ownership context, escaping, pending states, retained edits, inline cancellation, atomic edit handoff and late-response guards passed.');
})().catch(e=>{console.error(e);process.exitCode=1;});
