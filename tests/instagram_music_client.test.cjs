const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');

function setup(response){
 const nodes={},listeners={};
 const get=id=>nodes[id]??=( {hidden:false,textContent:'',value:'',innerHTML:'',open:false,disabled:false,
  addEventListener:(event,fn)=>listeners[id+':'+event]=fn,replaceChildren(){this.innerHTML='';},append(){},
  showModal(){this.open=true;},close(){this.open=false;listeners[id+':close']?.();}} );
 let saves=0;
 const context={window:{zovaWorkspaceUrl:p=>p},document:{getElementById:get,addEventListener:(_,fn)=>fn(),createElement:()=>({})},
  URLSearchParams,instagramFormat:()=>context.format,format:'post',uploadedMedia:[{id:1,filename:'video.mp4'}],uploadedMediaKind:'video',
  selectedPlatforms:()=>['instagram'],variants:{instagram:{posts:['Caption']}},workspaceEpoch:0,
  scheduleAutosave:()=>saves++,editableDraft:()=>true,esc:s=>String(s).replaceAll('<','&lt;'),api:response};
 vm.createContext(context);vm.runInContext(fs.readFileSync('nova/static/instagram-music.js','utf8'),context);
 return {context,nodes,get,listeners,music:context.window.zovaInstagramMusic,saves:()=>saves};
}
const track={audio_id:'123',title:'Synthetic track',artist:'Artist',preview_url:null};
const reply={eligible:true,tracks:[track],connection_id:4,accounts:[{id:4,name:'First'},{id:5,name:'Second'}]};

test('music binds the exact account and volumes; changing format cannot silently drop it',async()=>{
 const t=setup(async()=>reply);await t.music.open();
 assert.equal(t.get('instagramMusicAccountLabel').hidden,false);
 t.listeners['instagramMusicResults:click']({target:{closest:()=>({dataset:{track:'0'}})}});
 assert.equal(t.music.optionFor(4).audio_id,'123');assert.throws(()=>t.music.optionFor(5),/this Instagram account/);
 t.listeners['instagram_audio_volume:change']({target:{value:'101'}});assert.equal(t.music.snapshot().audio_volume,100);
 t.listeners['instagram_audio_volume:change']({target:{value:'40'}});assert.equal(t.music.optionFor(4).audio_volume,40);
 t.context.format='story';assert.throws(()=>t.music.optionFor(4),/single video Reel/);
 t.music.clear();assert.equal(t.music.optionFor(4),null);assert.ok(t.saves()>0);
});

test('late catalogue responses cannot overwrite a changed draft or a closed dialog',async()=>{
 for(const change of [t=>t.context.workspaceEpoch++,t=>t.get('instagramMusic').close()]){
  let finish;const t=setup(()=>new Promise(resolve=>finish=resolve));const waiting=t.music.open();
  change(t);finish(reply);await waiting;
  assert.equal(t.get('instagramMusicResults').innerHTML,'');assert.equal(t.music.snapshot(),null);
 }
});

test('Story and unsupported access expose the finish-in-Instagram path without a fake publish action',async()=>{
 let calls=0;const t=setup(async()=>{calls++;return {eligible:false,reason:'Not available',tracks:[]};});
 t.context.format='story';await t.music.open();assert.equal(calls,0);
 assert.equal(t.get('instagramFinish').open,true);assert.equal(t.get('instagramMusicSearch').hidden,true);
 assert.equal(t.get('instagramCopyCaption').hidden,true);
 t.context.format='post';await t.music.open();assert.equal(calls,1);assert.equal(t.get('instagramFinish').open,true);
});
