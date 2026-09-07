const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const calculator = fs.readFileSync(path.join(root,'position-calculator.js'),'utf8');
function weights(modelWeights, holding='SPY, TLT') {
  const source={dataset:modelWeights===undefined?{}:{modelWeights},querySelectorAll:()=>[{textContent:'Holding'}],querySelector:()=>({textContent:holding})};
  const panel={querySelector:s=>s==='h2'?{textContent:'Latest Alert'}:s==='.position-calculator'?null:source};
  const context={document:{querySelectorAll:()=>[panel]}};
  vm.runInNewContext(calculator.split('  if (!positions.length) return;')[0]+'  globalThis.result=positions;\n})();',context);
  return context.result && JSON.parse(JSON.stringify(context.result));
}
assert.deepEqual(weights('{"SPY":0.25,"BIL":0.75}'),[{ticker:'SPY',weight:.25},{ticker:'BIL',weight:.75}]);
assert.deepEqual(weights(undefined),[{ticker:'SPY',weight:.5},{ticker:'TLT',weight:.5}]);
assert.equal(weights('{"SPY":0.25,"BIL":0.5}'),undefined);
const member = fs.readFileSync(path.join(root,'api/_member-content/haa.html'),'utf8');
const encoded = member.match(/data-model-weights="([^"]+)"/)[1].replace(/&quot;/g,'"');
assert.deepEqual(weights(encoded),Object.entries(JSON.parse(encoded)).map(([ticker,weight])=>({ticker,weight})));
async function route(user,membership,strategy='haa') {
 const context={module:{exports:{}},console,__dirname:path.join(root,'api'),require:name=>name==='./_auth'?{getUser:async()=>user,getMembership:async()=>membership}:require(name)};
 vm.runInNewContext(fs.readFileSync(path.join(root,'api/member-page.js'),'utf8'),context);
 const result={headers:{},status(n){this.code=n;return this},send(body){this.body=body;return this},setHeader(k,v){this.headers[k]=v}};
 await context.module.exports({method:'GET',query:{strategy},headers:{}},result); return result;
}
(async()=>{
 assert.equal((await route(null,false)).code,401);
 assert.equal((await route({email:'member@example.invalid'},false)).code,403);
 const ok=await route({email:'member@example.invalid'},true);
 assert.equal(ok.code,200); assert.equal(ok.headers['Cache-Control'],'private, no-store');
 assert.match(ok.body,/<h1>Hybrid Asset Allocation \(HAA\)<\/h1>/); assert.match(ok.body,/detail-signout-button/);
 assert.equal((await route({email:'member@example.invalid'},true,'../haa')).code,404);
 assert.equal((await route({email:'member@example.invalid'},true,'momentum2')).code,200);
 console.log('PASS: explicit HAA weights, existing ETF equal weights, invalid weights, member 401/403/200, route allowlist, and ETF2 route');
})().catch(error=>{console.error(error);process.exitCode=1});
