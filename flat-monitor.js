'use strict';
const $ = id => document.getElementById(id);
const inputs = [...document.querySelectorAll('#tickers input')];
let token = '', configured = false, actionPending = false, lastSuccess = 0;
const money = n => typeof n === 'number' && Number.isFinite(n) ? '$' + n.toFixed(n < 10 ? 4 : 2) : '—';
const pt = value => value ? new Date(value).toLocaleTimeString('en-US', {timeZone:'America/Los_Angeles',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}) : '—';
function pacificCandle(value) { const [h,m]=value.slice(11,16).split(':').map(Number); return String((h+21)%24).padStart(2,'0')+':'+String(m).padStart(2,'0'); }
function el(tag, cls, text) { const node = document.createElement(tag); if(cls) node.className=cls; if(text!==undefined)node.textContent=text; return node; }
function card(row) {
 const color=(row.light||'GRAY').toLowerCase(), box=el('tr','ticker-row '+color+'-row');
 const ticker=el('td','ticker-cell');ticker.append(el('span','dot '+color),el('strong','symbol',row.symbol||'—'));box.append(ticker);
 box.append(el('td','number',money(row.current_price)));
 const available=row.status!=='UNKNOWN' && row.status!=='BYPASS' && !!row.symbol;
 const precise=n=>typeof n==='number'&&Number.isFinite(n)?'$'+n.toFixed(4):'—';
 box.append(el('td','number',available?precise(row.volatility_5m):'—'));
 const target=el('td','target-cell');
 target.append(el('strong','number',available?precise(row.qualify_price):'—'));
 target.append(el('small','',available&&typeof row.maximum_qualify_price==='number'?'Max '+precise(row.maximum_qualify_price):''));box.append(target);
 const reversal=el('td','reversal-cell');
 reversal.append(el('span',available&&row.reversal_in_progress?'reversal-active':'',!available?'—':row.reversal_in_progress?'In progress':'No'));
 if(available&&typeof row.reversal_drift_two==='number')reversal.append(el('small','',row.reversal_drift_two.toFixed(2)+'× V drift'));
 box.append(reversal);
 const labels={PASS:'Filter permits',BYPASS:'Before cutoff',WAIT:'Flat · wait',BLOCK:'Flat · blocked',UNKNOWN:'Unavailable'};
 const status=el('td','status-cell');status.append(el('span','badge',row.symbol?(labels[row.status]||'Unavailable'):'Add a ticker'),el('small','',row.description||'Your ticker status will appear here.'));box.append(status);
 const timing=el('td','timing-cell');timing.append(el('span','',available&&row.signal_end?pacificCandle(row.signal_end)+' PT':'—'),el('small','',row.checked_at?'Updated '+pt(row.checked_at):''));box.append(timing);
 return box;
}
function render(state) {
 token=state.csrf;
 document.querySelector('.brand small').textContent='TRADESTATION · '+(state.filter_version||'PREVIOUS VERSION');
 if(!configured) {inputs.forEach((n,i)=>n.value=state.symbols[i]||'');$('cutoff').value=state.cutoff;configured=true;}
 inputs.forEach(n=>n.disabled=(state.busy&&!state.running)||actionPending);$('cutoff').disabled=state.busy||actionPending;
 $('start').disabled=state.remote_online===false||(state.busy&&!state.running)||actionPending;$('stop').disabled=!state.running||actionPending;
 $('start').textContent=state.running?'Update tickers':'Start monitoring';
 $('notice').textContent=state.notice;
 $('connection').textContent=state.remote_online===false?'PC offline':state.running?'Monitoring':state.busy?'Stopping':'Connected';
 $('connection-dot').className='green';
 $('cards').replaceChildren(...Array.from({length:5},(_,i)=>card(state.rows[i]||{})));
 for(const color of ['GREEN','ORANGE','GRAY'])$(color.toLowerCase()+'-count').textContent=state.rows.filter(r=>r.light===color).length;
 const activity=$('activity');activity.replaceChildren();
 if(!state.history.length)activity.append(el('p','empty','Status changes will appear here once monitoring starts.'));
 state.history.slice(0,8).forEach(r=>{const line=el('div','event');line.append(el('time','',pt(r.checked_at)),el('span','dot '+r.light.toLowerCase()),el('strong','',r.symbol),el('span','message',r.description));activity.append(line);});
}
function disconnected(){
 $('connection').textContent='Disconnected';$('connection-dot').className='gray';
 $('notice').textContent='Dashboard connection lost. Lights are unavailable until updates resume.';
 $('cards').replaceChildren(...inputs.map(n=>card({symbol:n.value,status:'UNKNOWN',light:'GRAY',description:'Connection lost — waiting for the local server'})));
 $('green-count').textContent='0';$('orange-count').textContent='0';$('gray-count').textContent=inputs.filter(n=>n.value).length;
 $('start').disabled=true;$('stop').disabled=true;
}
async function refresh(){try{const response=await remoteFetch('/api/state',{signal:AbortSignal.timeout(5000)});if(!response.ok)throw Error();const state=await response.json();lastSuccess=Date.now();render(state);}catch(e){disconnected();$('notice').textContent=e.message;}finally{setTimeout(refresh,5000);}}
async function action(path,body){
 actionPending=true;$('start').disabled=true;$('stop').disabled=true;
 try{const response=await remoteFetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-Dashboard-Token':token},body:JSON.stringify(body),signal:AbortSignal.timeout(5000)});const data=await response.json();if(!response.ok)throw Error(data.error||'Request failed');actionPending=false;render(data);}
 catch(e){$('notice').textContent=e.message;}
 finally{actionPending=false;}
}
$('watch-form').addEventListener('submit',e=>{e.preventDefault();action('/api/start',{symbols:inputs.map(n=>n.value.trim().toUpperCase()).filter(Boolean),cutoff:$('cutoff').value});});
$('stop').addEventListener('click',()=>action('/api/stop',{}));
$('cards').replaceChildren(...Array.from({length:5},()=>card({})));
setInterval(()=>{$('clock').textContent=pt(new Date())+' PT';if(lastSuccess&&Date.now()-lastSuccess>7000)disconnected();},1000);
refresh();
