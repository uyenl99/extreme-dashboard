const {getUser, required, sendJson} = require('./_auth');
const {timingSafeEqual, createHash, randomUUID} = require('node:crypto');
const CUTOFFS = new Set(['09:30','10:45','11:00','11:30','12:00']);
function same(a,b) { return timingSafeEqual(createHash('sha256').update(a).digest(),createHash('sha256').update(b).digest()); }
function validCommand(body) {
  if (body.action === 'stop') return {action:'stop'};
  const symbols=body.symbols;
  if(body.action!=='start'||!Array.isArray(symbols)||symbols.length<1||symbols.length>5||
    symbols.some(s=>typeof s!=='string'||! /^[A-Z0-9][A-Z0-9./-]{0,19}$/.test(s))||
    new Set(symbols).size!==symbols.length||!CUTOFFS.has(body.cutoff)) throw Error('Invalid command');
  return {action:'start',symbols,cutoff:body.cutoff};
}
async function record(method='GET',body) {
  const key=required('FLAT_MONITOR_DB_SECRET');
  const headers={apikey:key,'Content-Type':'application/json',Prefer:'return=representation'};
  if(!key.startsWith('sb_secret_')) headers.Authorization='Bearer '+key;
  const response=await fetch(required('SUPABASE_URL')+'/rest/v1/flat_monitor_relay?id=eq.1',{
    method,headers,body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(8000)});
  if(!response.ok) throw Error('Relay storage unavailable');
  const rows=await response.json();if(rows.length!==1)throw Error('Relay not initialized');return rows[0];
}
function publicState(row) {
  const state=row.snapshot||{};
  const age=Date.now()-Date.parse(row.updated_at||'');
  const online=Number.isFinite(age)&&age>=-5000&&age<45000;
  const pending=row.command_id && row.command_id!==row.ack_id && Date.now()-Date.parse(row.requested_at)<60000;
  const rows=(state.rows||[]).map(r=>{
    const checked=Date.parse(r.checked_at||'');
    const fresh=Number.isFinite(checked)&&Date.now()-checked<45000&&checked<=Date.now()+5000;
    return online&&fresh&&state.running?r:{...r,status:'UNKNOWN',light:'GRAY',description:online?'Waiting for fresh monitor data':'PC disconnected / data expired'};
  });
  return {...state,rows,symbols:state.symbols||[],cutoff:state.cutoff||'11:00',history:state.history||[],
    running:online&&!!state.running,busy:online&&!!state.busy,remote_online:online,csrf:'',
    notice:!online?'PC is offline. Start the dashboard and remote relay on your PC.':pending?'Change sent; waiting for the PC to apply it.':state.notice};
}
module.exports=async function handler(req,res) {
  if(!['GET','POST'].includes(req.method))return sendJson(res,405,{error:'Method not allowed'});
  try {
    if(JSON.stringify(req.body||{}).length>100000)return sendJson(res,413,{error:'Request too large'});
    if(req.method==='POST'&&req.body?.action==='publish') {
      const expected=required('FLAT_MONITOR_DEVICE_KEY');
      if(expected.length<32||!same(req.headers.authorization||'','Bearer '+expected))return sendJson(res,401,{error:'Unauthorized device'});
      const s=req.body.state;
      if(!s||!Array.isArray(s.rows)||s.rows.length>5)return sendJson(res,400,{error:'Invalid state'});
      // Never store the local dashboard CSRF token or any broker credentials.
      const snapshot={};
      for(const k of ['filter_version','running','busy','symbols','cutoff','rows','history','notice'])snapshot[k]=s[k];
      const row=await record('PATCH',{snapshot,updated_at:new Date().toISOString(),ack_id:req.body.ack_id||null});
      return sendJson(res,200,{command:row.command,command_id:row.command_id,requested_at:row.requested_at,ack_id:row.ack_id});
    }
    const user=await getUser(req);
    if(!user)return sendJson(res,401,{error:'Please sign in to your website account.'});
    if(!user.email_confirmed_at||user.email?.toLowerCase()!==required('FLAT_MONITOR_OWNER_EMAIL').toLowerCase())return sendJson(res,403,{error:'This monitor is private to its owner.'});
    if(req.method==='GET')return sendJson(res,200,publicState(await record()));
    let command;try{command=validCommand(req.body||{});}catch{return sendJson(res,400,{error:'Invalid watchlist or cutoff'});}
    const current=await record();
    if(!publicState(current).remote_online)return sendJson(res,409,{error:'PC offline. Reconnect it before sending changes.'});
    const row=await record('PATCH',{command,command_id:randomUUID(),requested_at:new Date().toISOString()});
    return sendJson(res,200,publicState(row));
  } catch {return sendJson(res,503,{error:'Remote monitor is not configured or temporarily unavailable.'});}
};
module.exports.validCommand=validCommand;
module.exports.publicState=publicState;
