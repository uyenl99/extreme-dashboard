'use strict';
let configPromise, refreshPromise;
async function remoteFetch(path,options={}) {
  let session;
  try {session=JSON.parse(localStorage.getItem('eti_member_session'));}catch{}
  if(!session?.access_token)throw Error('Sign in using the website login link above, then return here.');
  if(!session.expires_at||session.expires_at<Date.now()/1000+60){
    if(!refreshPromise)refreshPromise=(async()=>{
      configPromise ||= fetch('/api/public-config').then(r=>r.json());
      const cfg=await configPromise;
      const r=await fetch(cfg.supabaseUrl+'/auth/v1/token?grant_type=refresh_token',{method:'POST',headers:{apikey:cfg.supabaseAnonKey,'Content-Type':'application/json'},body:JSON.stringify({refresh_token:session.refresh_token})});
      if(!r.ok)throw Error('Website session expired. Please sign in again.');
      const data=await r.json();const next={access_token:data.access_token,refresh_token:data.refresh_token,expires_at:Date.now()/1000+data.expires_in};
      localStorage.setItem('eti_member_session',JSON.stringify(next));return next;
    })().finally(()=>{refreshPromise=null;});
    session=await refreshPromise;
  }
  let body;
  if(options.method==='POST')body=JSON.stringify({...JSON.parse(options.body||'{}'),action:path.endsWith('/stop')?'stop':'start'});
  const response=await fetch('/api/flat-monitor',{method:options.method||'GET',body,
    headers:{'Content-Type':'application/json',Authorization:'Bearer '+session.access_token},signal:options.signal});
  if(!response.ok){const data=await response.json();throw Error(data.error||'Remote monitor unavailable');}
  return response;
}
