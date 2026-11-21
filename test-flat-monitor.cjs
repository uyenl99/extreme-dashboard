const test=require('node:test');const assert=require('node:assert/strict');
const handler=require('./api/flat-monitor');
process.env.SUPABASE_URL='https://test.supabase.co';process.env.SUPABASE_ANON_KEY='public';
process.env.FLAT_MONITOR_DB_SECRET='sb_secret_test';process.env.FLAT_MONITOR_OWNER_EMAIL='owner@example.com';
process.env.FLAT_MONITOR_DEVICE_KEY='a'.repeat(40);
async function call(req){let code,body;const res={setHeader(){},status(c){code=c;return this},json(b){body=b}};await handler(req,res);return {code,body};}
test('unauthenticated and other users cannot access monitor',async()=>{
  assert.equal((await call({method:'GET',headers:{}})).code,401);
  global.fetch=async()=>({ok:true,json:async()=>({email:'other@example.com',email_confirmed_at:'2026-01-01'})});
  assert.equal((await call({method:'GET',headers:{authorization:'Bearer other'}})).code,403);
});
test('confirmed owner can read; offline data never gives green',async()=>{
  let i=0;global.fetch=async()=>({ok:true,json:async()=>++i===1?{email:'owner@example.com',email_confirmed_at:'2026-01-01'}:[{snapshot:{symbols:['NN'],rows:[{symbol:'NN',light:'GREEN',status:'PASS',checked_at:new Date().toISOString()}],running:true},updated_at:'2020-01-01'}]});
  const result=await call({method:'GET',headers:{authorization:'Bearer owner'}});
  assert.equal(result.code,200);assert.equal(result.body.rows[0].light,'GRAY');assert.equal(result.body.running,false);
});
test('unconfirmed owner denied',async()=>{
  global.fetch=async()=>({ok:true,json:async()=>({email:'owner@example.com'})});
  assert.equal((await call({method:'GET',headers:{authorization:'Bearer owner'}})).code,403);
});
test('device requires secret; publication strips local CSRF',async()=>{
  assert.equal((await call({method:'POST',headers:{},body:{action:'publish'}})).code,401);
  let published;global.fetch=async(url,opts)=>{published=JSON.parse(opts.body);return {ok:true,json:async()=>[{}]}};
  const result=await call({method:'POST',headers:{authorization:'Bearer '+'a'.repeat(40)},body:{action:'publish',state:{rows:[],symbols:[],csrf:'never-leave-pc'}}});
  assert.equal(result.code,200);assert.equal(published.snapshot.csrf,undefined);
});
test('only validated ticker actions supported',()=>{
  assert.deepEqual(handler.validCommand({action:'stop',url:'https://bad'}),{action:'stop'});
  for(const value of [{action:'exec'}, {action:'start',symbols:['NN','NN'],cutoff:'11:00'}, {action:'start',symbols:['<script>'],cutoff:'11:00'}])assert.throws(()=>handler.validCommand(value));
});
test('fresh heartbeat cannot revive old quote',()=>{
  const result=handler.publicState({updated_at:new Date().toISOString(),snapshot:{running:true,rows:[{checked_at:'2020-01-01',light:'GREEN'}]}});
  assert.equal(result.rows[0].light,'GRAY');
});
