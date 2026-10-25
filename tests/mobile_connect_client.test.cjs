const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

function fixture(){
 class Node{
  constructor(tag){this.tag=tag;this.children=[];this.attrs={};this.disabled=false;this.textContent='';this.events={};}
  appendChild(child){child.parent=this;this.children.push(child);}
  remove(){this.parent.children=this.parent.children.filter(node=>node!==this);}
  setAttribute(name,value){this.attrs[name]=value;}
  removeAttribute(name){delete this.attrs[name];}
  addEventListener(name,handler){this.events[name]=handler;}
  querySelectorAll(){return this.children.filter(node=>node.tag==='button');}
  querySelector(){return this.querySelectorAll()[0];}
 }
 const forms=['direct','facebook','cancel'].map(value=>{
  const form=new Node('form'),button=new Node('button'),proof=new Node('input');
  button.name=value==='cancel'?'decision':'method';button.value=value;button.textContent=value;
  proof.type='hidden';proof.name='proof';proof.value='synthetic-proof';
  form.appendChild(button);form.appendChild(proof);return form;
 });
 const events={},timers=new Map();let next=0;
 const context={document:{querySelectorAll:()=>forms,createElement:tag=>new Node(tag)},window:{addEventListener:(name,handler)=>events[name]=handler},setTimeout:handler=>{timers.set(++next,handler);return next;},clearTimeout:id=>timers.delete(id)};
 vm.createContext(context);vm.runInContext(fs.readFileSync('nova/static/mobile-connect.js','utf8'),context);
 const submit=(index,extra={})=>{
  const form=forms[index],event={submitter:form.querySelector(),defaultPrevented:false,preventDefault(){this.defaultPrevented=true},...extra};
  form.events.submit(event);return event;
 };
 const payload=index=>Object.fromEntries(forms[index].children.filter(node=>node.name&&!node.disabled).map(node=>[node.name,node.value]));
 return {forms,events,timers,submit,payload};
}

test('pending handoff preserves selected method and proof while stopping repeat submissions',()=>{
 for(const [index,name,value] of [[0,'method','direct'],[1,'method','facebook'],[2,'decision','cancel']]){
  const t=fixture();const sent=t.submit(index);
  assert.equal(sent.defaultPrevented,false);
  assert.deepEqual(t.payload(index),{proof:'synthetic-proof',[name]:value});
  assert.equal(t.forms[index].attrs['aria-busy'],'true');
  assert.equal(t.forms[index].querySelector().textContent,index===2?'Opening account options…':'Connecting…');
  assert.ok(t.forms.every(form=>form.querySelector().disabled));
  assert.equal(t.submit(index).defaultPrevented,true);
  assert.equal(t.submit((index+1)%3).defaultPrevented,true);
 }
});

test('browser back restores controls and removes the temporary successful control',()=>{
 const t=fixture();t.submit(1);t.events.pagehide();assert.equal(t.timers.size,0);t.events.pageshow();
 assert.ok(t.forms.every(form=>!form.querySelector().disabled));
 assert.equal(t.forms[1].querySelector().textContent,'facebook');
 assert.equal(t.forms[1].attrs['aria-busy'],undefined);
 assert.equal(t.forms[1].children.filter(node=>node.tag==='input'&&node.name==='method').length,0);
 assert.equal(t.submit(0).defaultPrevented,false);
 assert.deepEqual(t.payload(0),{proof:'synthetic-proof',method:'direct'});
});

test('stopped or failed navigation re-enables the form with a useful retry message',()=>{
 const t=fixture();t.submit(0);[...t.timers.values()][0]();
 assert.ok(t.forms.every(form=>!form.querySelector().disabled));
 assert.match(t.forms[0].children.find(node=>node.attrs.role==='status').textContent,/Try again/);
 assert.equal(t.submit(0).defaultPrevented,false);
 assert.equal(t.forms[0].children.filter(node=>node.attrs.role==='status').length,1);
});

test('already-cancelled submissions do not disable forms, keyboard submit keeps method',()=>{
 const t=fixture();t.submit(0,{defaultPrevented:true});
 assert.ok(t.forms.every(form=>!form.querySelector().disabled));assert.equal(t.timers.size,0);
 t.submit(0,{submitter:null});assert.deepEqual(t.payload(0),{proof:'synthetic-proof',method:'direct'});
});
