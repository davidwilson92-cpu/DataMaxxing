/* Refresh connection presentation without reloading or discarding a draft. */
window.refreshNativeConnections=async function(){
 try{
  if(typeof connectionData==='undefined'){
   const current=document.getElementById('socials');
   if(!current)return;
   const response=await fetch(window.zovaWorkspaceUrl?window.zovaWorkspaceUrl('/account'):'/account',{cache:'no-store'});
   if(!response.ok)return;
   const fresh=new DOMParser().parseFromString(await response.text(),'text/html').getElementById('socials');
   if(!fresh)return;
   for(const control of fresh.querySelectorAll('a[href],form[action]')){
    const attribute=control.tagName==='FORM'?'action':'href';
    const url=new URL(control.getAttribute(attribute),location.href);
    if(url.origin===location.origin&&window.zovaWorkspaceUrl)control.setAttribute(attribute,window.zovaWorkspaceUrl(url.href));
   }
   current.replaceWith(fresh);
   return;
  }
  const response=await fetch(window.zovaWorkspaceUrl?window.zovaWorkspaceUrl('/api/native-connections'):'/api/native-connections',{cache:'no-store'});
  if(!response.ok)return;
  const data=await response.json();
  for(const platform of ['instagram','facebook','x','tiktok'])connectionData[platform]=data.connections[platform]||[];
  if(typeof renderReadiness==='function')renderReadiness();
 }catch(_){/* Existing work remains usable while offline. */}
};
