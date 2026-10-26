const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

function setup(reply){
 const nodes={},fields={};let listener;
 for(const key of ['writing_tone','audience','topics','things_to_avoid','example_posts','preferred_post_length'])fields[key]={value:''};
 for(const key of ['scanResult','voiceStatusTitle','voiceStatusText','voiceSavedAt'])nodes[key]={textContent:'',hidden:true};
 nodes.rescanVoice={disabled:false,textContent:'Scan recent posts',addEventListener:(_,fn)=>listener=fn};
 nodes.voicePreferences={elements:{namedItem:key=>fields[key]}};
 const context={window:{addEventListener(){}},location:{hash:''},document:{getElementById:id=>nodes[id]},fetch:reply};
 vm.createContext(context);vm.runInContext(fs.readFileSync('nova/static/account-sections.js','utf8'),context);
 return {nodes,fields,scan:()=>listener()};
}

test('successful scan displays the persisted profile without requiring reload',async()=>{
 const t=setup(async()=>({ok:true,json:async()=>({status:'learned',posts_scanned:4,preferences:{writing_tone:'Warm',audience:'Creators'},overrides:[]})}));
 await t.scan();assert.equal(t.fields.writing_tone.value,'Warm');assert.equal(t.fields.audience.value,'Creators');
 assert.equal(t.nodes.voiceStatusText.textContent,'Warm');assert.match(t.nodes.scanResult.textContent,/4 captions/);assert.equal(t.nodes.rescanVoice.disabled,false);
});

test('late scan response preserves edits made while the provider was running',async()=>{
 let finish;const t=setup(()=>new Promise(resolve=>finish=resolve));
 const pending=t.scan();t.fields.writing_tone.value='My unsaved correction';
 finish({ok:true,json:async()=>({status:'learned',posts_scanned:2,preferences:{writing_tone:'Learned tone'},overrides:[]})});await pending;
 assert.equal(t.fields.writing_tone.value,'My unsaved correction');assert.match(t.nodes.scanResult.textContent,/unsaved edits are kept/);
});

test('empty scans and failures do not blank fields or announce successful learning',async()=>{
 for(const reply of [{ok:true,data:{status:'waiting',message:'No readable captions'}},{ok:false,data:{detail:'Your saved voice is unchanged.'}}]){
  const t=setup(async()=>({ok:reply.ok,json:async()=>reply.data}));t.fields.writing_tone.value='Saved tone';
  await t.scan();assert.equal(t.fields.writing_tone.value,'Saved tone');assert.doesNotMatch(t.nodes.scanResult.textContent,/Learned from/);assert.equal(t.nodes.rescanVoice.disabled,false);
 }
});
