const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('nova/static/ios-shell.js','utf8');

test('deep links expand the correct account category without clearing other settings',()=>{
 const group={tagName:'DETAILS',open:false,parentElement:null},target={tagName:'SECTION',parentElement:group,scrollIntoView(){this.scrolled=true}};
 let onHash;
 const context={location:{hash:'#socials'},document:{getElementById:id=>id==='socials'?target:null},window:{addEventListener:(event,fn)=>onHash=fn}};
 vm.createContext(context);vm.runInContext(fs.readFileSync('nova/static/account-sections.js','utf8'),context);
 assert.equal(group.open,true);assert.equal(target.scrolled,true);
 context.location.hash='#%invalid';assert.doesNotThrow(()=>onHash());
});

test('mobile composer focus tracks keyboard layout and resets after blur',()=>{
 const classes=new Set(),properties={};
 const context={window:{innerWidth:393,visualViewport:{height:420}},document:{activeElement:{id:'brief'},
  body:{classList:{toggle:(name,on)=>on?classes.add(name):classes.delete(name)}},
  querySelector:()=>({style:{setProperty:(name,value)=>properties[name]=value}})}};
 const experience=fs.readFileSync('nova/static/studio-experience.js','utf8');
 vm.createContext(context);vm.runInContext(experience.slice(experience.indexOf('function fitVisibleViewport()'),experience.indexOf("document.getElementById('brief').addEventListener('focus'")),context);
 vm.runInContext('fitVisibleViewport()',context);
 assert.equal(properties['--chat-height'],'420px');assert.equal(classes.has('composer-keyboard-open'),true);
 context.document.activeElement=null;vm.runInContext('fitVisibleViewport()',context);assert.equal(classes.size,0);
 context.window.innerWidth=1200;vm.runInContext('fitVisibleViewport()',context);assert.equal(properties['--chat-height'],'100dvh');
});

test('returning from connection refreshes Studio destinations without clearing the idea',async()=>{
 const input={value:'My unsaved idea'},data={instagram:[],x:['Old account']};let rendered=0;
 const context={window:{},connectionData:data,renderReadiness:()=>rendered++,input,
  fetch:async()=>({ok:true,json:async()=>({connections:{instagram:['New creator'],x:['My X']}})})};
 vm.createContext(context);vm.runInContext(source,context);await context.window.refreshNativeConnections();
 assert.deepEqual(data.instagram,['New creator']);assert.deepEqual(data.x,['My X']);assert.equal(data.facebook.length,0);
 assert.equal(input.value,'My unsaved idea');assert.equal(rendered,1);
});

test('Account refresh replaces only socials and pins new links/forms to the current workspace',async()=>{
 const profile={value:'Unsaved profile edit'};let replaced;
 const controls=['A','FORM'].map(tagName=>({tagName,value:'/connect/x',getAttribute(){return this.value},setAttribute(k,v){this.value=v}}));
 const fresh={querySelectorAll:()=>controls};
 const context={window:{zovaWorkspaceUrl:path=>{const url=new URL(path,'https://zova-social.com');url.searchParams.set('workspace','8');return url.pathname+url.search}},
  location:{href:'https://zova-social.com/account?workspace=8',origin:'https://zova-social.com'},URL,profile,
  document:{getElementById:id=>id==='socials'?{replaceWith:node=>replaced=node}:profile},
  DOMParser:class{parseFromString(){return {getElementById:()=>fresh}}},
  fetch:async path=>{assert.equal(path,'/account?workspace=8');return {ok:true,text:async()=>'<section id="socials">Connected</section>'}}};
 vm.createContext(context);vm.runInContext(source,context);await context.window.refreshNativeConnections();
 assert.equal(replaced,fresh);assert.equal(profile.value,'Unsaved profile edit');
 for(const control of controls)assert.equal(control.value,'/connect/x?workspace=8');
});

test('failed account refresh preserves existing connections and unsaved profile input',async()=>{
 let replaced=false;const profile={value:'Keep this'};
 const context={window:{},profile,document:{getElementById:()=>({replaceWith:()=>replaced=true})},fetch:async()=>({ok:false})};
 vm.createContext(context);vm.runInContext(source,context);await context.window.refreshNativeConnections();
 assert.equal(replaced,false);assert.equal(profile.value,'Keep this');
});
