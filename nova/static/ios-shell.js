/* Refresh connection presentation without reloading or discarding a draft. */
window.refreshNativeConnections=async function(){
 if(typeof connectionData==='undefined')return;
 try{
  const response=await fetch(window.zovaWorkspaceUrl?window.zovaWorkspaceUrl('/api/native-connections'):'/api/native-connections',{cache:'no-store'});
  if(!response.ok)return;
  const data=await response.json();
  for(const platform of ['instagram','facebook','x','tiktok'])connectionData[platform]=data.connections[platform]||[];
  if(typeof renderReadiness==='function')renderReadiness();
 }catch(_){/* Existing work remains usable while offline. */}
};
