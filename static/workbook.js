'use strict';
const $ = id => document.getElementById(id);
const csrf = document.querySelector('meta[name="csrf-token"]').content;
let mode = 'learn', bank = [], queue = [], states = {}, position = 0, requestVersion = 0;
let saving = Promise.resolve(), draftTimer, searchTimer, loading = false, revealed = false;
const names = {learn:'Learn',weak:'Weak',quick:'Quick Recall',data:'Data Drill',concepts:'Concepts & Reasoning',institutions:'Institutions',chapter:'Chapter Recall',bookmarked:'Bookmarked'};
function el(tag, text, className) {const node = document.createElement(tag);if (text !== undefined) node.textContent = text;if(className) node.className = className;return node;}
function status(message) {$('status').textContent=message;}
function current() {return bank.find(q => q.id === queue[position]);}
function draft() {const q=current();if(!q)return null;if(q.format==='recall')return $('response').value;return Object.fromEntries([...document.querySelectorAll('[data-blank]')].map(input=>[input.dataset.blank,input.value]));}
async function api(url, options={}) {const response=await fetch(url,options);if(!response.ok)throw Error(`Request failed (${response.status}).`);return response.json();}
function write(qid,payload) {
  const job=saving.catch(()=>{}).then(()=>api(`/api/progress/${encodeURIComponent(qid)}`,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify(payload)}));
  // Keep later navigation recoverable even when a prior write failed.
  saving=job.catch(()=>{});
  return job.then(result=>{states[qid]=result.state;renderMastery(result.mastery);return result;});
}
async function saveDraft() {
  clearTimeout(draftTimer);const q=current();if(!q)return;
  const value=draft();
  if(JSON.stringify(value)===JSON.stringify(states[q.id]?.draft))return saving;
  return write(q.id,{draft:value});
}
function scheduleDraft() {clearTimeout(draftTimer);draftTimer=setTimeout(()=>saveDraft().catch(()=>status('Your response could not be saved. Keep this page open and try again.')),300);}
function updatePages() {
  const selected=$('chapter').selectedOptions[0];$('page').replaceChildren(el('option','All pages'));$('page').firstChild.value='';
  if(selected?.dataset.start)for(let n=Number(selected.dataset.start);n<=Number(selected.dataset.end);n++){const option=el('option',`Page ${n}`);option.value=n;$('page').append(option);}
  $('page').disabled=!$('chapter').value;
}
function updateSubjects() {
  const subject=$('subject').value;
  for(const option of $('chapter').options)if(option.value)option.hidden=option.dataset.subject!==subject;
  if($('chapter').selectedOptions[0]?.hidden)$('chapter').value='';
  updatePages();
}
async function load() {
  const version=++requestVersion;
  loading=true;status('Loading your revision view…');
  try {
    await saveDraft();
    const params=new URLSearchParams({mode,chapter:$('chapter').value,subject:$('subject').value,page:$('page').value,search:$('search').value});
    const result=await api(`/api/workbook?${params}`);
    if(version!==requestVersion)return;
    bank=result.questions;states=result.states;queue=bank.map(q=>q.id);position=0;
    renderMastery(result.mastery);
    $('mode-title').textContent=$('search').value.trim()?'Search results':names[mode];
    $('clear-search').hidden=!$('search').value;
    $('question-count').textContent=`${bank.length} question${bank.length===1?'':'s'}`;
    status($('search').value.trim()?'Searching all chapters and revision categories.':mode==='weak'?'Due questions first. Again items return sooner; Good items leave this pool.':'');
    renderQuestion();
  }catch(error){status('Unable to load or save progress. Check that the local server is running, then change the view to retry.');}
  finally{if(version===requestVersion)loading=false;}
}
function renderMastery(counts) {
  $('mastery').replaceChildren();
  for(const [id, count] of Object.entries(counts)) {
    const option=[...$('chapter').options].find(o=>o.value===id);if(!option)continue;
    if($('chapter').value && $('chapter').value!==id && !$('search').value.trim())continue;
    if(option.hidden && !$('search').value.trim())continue;
    const block=el('div',undefined,'mastery-item');block.append(el('p',option.textContent,'mastery-title'));
    const values=el('div',undefined,'mastery-values');
    for(const [key,label] of [['strong','Strong'],['hard','Hard'],['weak','Weak'],['unseen','Unseen']]){const span=el('span');span.append(`${label} `,el('strong',count[key]));values.append(span);}
    const total=count.strong+count.hard+count.weak+count.unseen;
    const bar=el('div',undefined,'mastery-bar');bar.setAttribute('aria-hidden','true');
    for(const key of ['strong','hard','weak']){const segment=el('span',undefined,key);segment.style.width=`${total?100*count[key]/total:0}%`;bar.append(segment);}
    block.append(values,bar);if(count.due)block.append(el('div',`${count.due} due for review`,'due-note'));$('mastery').append(block);
  }
}
function normalise(value, blank) {
  const text=value.trim().toLocaleLowerCase().replaceAll('–','-').replaceAll('−','-');
  if(blank.input_mode==='decimal' && /^[-+]?\d+(?:,\d+)*(?:\.\d+)?$/.test(text))return String(Number(text.replaceAll(',','')));
  return text.replace(/\s+/g,' ');
}
function revealBlank(blank,input,result, check) {
  const matched=[blank.answer,...blank.accepted_answers].some(answer=>normalise(input.value,blank)===normalise(answer,blank));
  result.textContent=check?(matched?`Correct: ${blank.answer}`:`Expected: ${blank.answer}`):`Answer: ${blank.answer}`;
  result.hidden=false;
  if(check){input.setAttribute('aria-invalid',String(!matched));}
}
function fillPrompt(q) {
  const paragraph=el('div',undefined,'blank-prompt');
  const parts=q.prompt.split(/(\{\{\w+\}\})/g);
  for(const part of parts) {
    const match=/^\{\{(\w+)\}\}$/.exec(part);
    if(!match){paragraph.append(document.createTextNode(part));continue;}
    const blank=q.blanks.find(b=>b.id===match[1]);
    const group=el('span',undefined,'blank-group');const input=el('input');
    input.dataset.blank=blank.id;input.id=`blank-${blank.id}`;input.type='text';input.inputMode=blank.input_mode;
    input.autocomplete='off';input.setAttribute('aria-label',`${blank.label}: ${q.tags[0]}`);input.placeholder='…';
    input.value=states[q.id]?.draft?.[blank.id]||'';
    if(blank.input_mode==='text')input.style.width='11rem';
    input.addEventListener('input',scheduleDraft);
    const result=el('span',undefined,'blank-result');result.hidden=true;result.setAttribute('aria-live','polite');
    const check=el('button','Check');check.type='button';check.setAttribute('aria-label',`Check ${blank.label}`);check.addEventListener('click',()=>revealBlank(blank,input,result,true));
    const reveal=el('button','Reveal');reveal.type='button';reveal.setAttribute('aria-label',`Reveal ${blank.label}`);reveal.addEventListener('click',()=>revealBlank(blank,input,result,false));
    group.append(input,check,reveal,result);paragraph.append(group);
  }
  $('response-area').append(paragraph);
}
function renderQuestion() {
  const q=current();revealed=false;
  $('paper-placeholder')?.remove();
  $('question-panel').hidden=!q;$('empty').hidden=!!q;
  $('expected').hidden=true;$('rating-area').hidden=true;$('history-content').hidden=true;
  if(!q){
    const completed=queue.length>0;
    $('empty-title').textContent=completed?'Revision pass complete':'No questions in this view';
    $('empty-description').textContent=completed?'Your ratings are saved. Open Weak to revisit difficult material or Chapter Recall to reconstruct the chapter.':
      mode==='weak'?'No Again or Hard questions match these filters. Rate recalled material in Learn to build your weak pool.':
      mode==='bookmarked'?'Bookmark questions while studying to collect them here.':
      $('search').value.trim()?'Try another keyword. Search checks prompts, answers, terminology and reports across the whole workbook.':'Try another chapter, page or revision mode.';
    return;
  }
  const state=states[q.id];
  const pageText=q.source_pages.length===1?`Page ${q.source_pages[0]}`:`Pages ${q.source_pages.join(', ')}`;
  $('source-ref').textContent=`Chapter ${q.chapter_number} • ${pageText}`;
  $('bookmark').setAttribute('aria-pressed',String(!!state?.bookmarked));$('bookmark').textContent=state?.bookmarked?'★ Bookmarked':'☆ Bookmark';
  $('type-label').textContent=q.scope==='chapter'?'Chapter recall':q.format==='fill_blank'?'Fill in the blanks':q.category.replaceAll('_',' ');
  $('position').textContent=`${position+1} / ${queue.length}`;
  $('question-title').textContent=q.format==='fill_blank'?q.tags[0]:q.prompt;
  $('response-area').replaceChildren();
  if(q.format==='fill_blank')fillPrompt(q);
  else{const label=el('label','Your recall — keywords, bullets or a reasoning chain');label.htmlFor='response';const input=el('textarea');input.id='response';input.placeholder='Retrieve what you remember before revealing…';input.value=state?.draft||'';input.addEventListener('input',scheduleDraft);$('response-area').append(label,input);}
  $('reveal').textContent=q.format==='fill_blank'?'Check / Reveal all':'Reveal answer';$('reveal').disabled=false;
  $('source-links').replaceChildren();
  const link=el('a',q.source_pages.length===1?'View Source':`View Source · p. ${q.source_pages[0]}`);link.href=`/source/${encodeURIComponent(q.source_id)}#page=${q.source_pages[0]}`;link.target='_blank';link.rel='noopener';$('source-links').append(link);
  if(q.source_pages.length>1){const details=el('details');details.append(el('summary','Other pages'));for(const page of q.source_pages.slice(1)){const a=el('a',`p. ${page}`);a.href=`/source/${encodeURIComponent(q.source_id)}#page=${page}`;a.target='_blank';a.rel='noopener';details.append(a,document.createTextNode(' '));}$('source-links').append(details);}
  $('previous').disabled=position===0;
  for(const button of document.querySelectorAll('[data-rating]'))button.disabled=false;
}
async function revealAll() {
  if(!current()||loading)return;
  try{await saveDraft();}catch{status('Your response could not be saved; you can still recall and reveal.');}
  const q=current();if(!q)return;
  if(q.format==='fill_blank')for(const blank of q.blanks){const input=$(`blank-${blank.id}`);revealBlank(blank,input,input.parentElement.querySelector('.blank-result'),true);}
  $('expected-content').replaceChildren();
  if(q.format==='fill_blank'){
    const list=el('ul');q.blanks.forEach((b,i)=>list.append(el('li',`Blank ${i+1}: ${b.answer}`)));$('expected-content').append(list);
  }else{
    const list=el(q.expected_answer.style==='chain'?'div':'ul');
    for(const text of q.expected_answer.items)list.append(el(q.expected_answer.style==='chain'?'p':'li',text,q.expected_answer.style==='chain'?'chain':''));
    $('expected-content').append(list);
  }
  $('source-note').textContent=q.source_note||'';$('source-note').hidden=!q.source_note;
  $('expected').hidden=false;$('rating-area').hidden=false;$('reveal').disabled=true;revealed=true;
}
async function rate(rating) {
  if(!revealed||loading)return;
  const q=current();if(!q)return;
  loading=true;for(const b of document.querySelectorAll('[data-rating]'))b.disabled=true;
  try{
    await saveDraft();const result=await write(q.id,{rating,draft:draft()});
    if(mode==='weak'&&!$('search').value.trim()) {
      if(rating==='good')queue=queue.filter((id,i)=>i<=position||id!==q.id);
      const distance=rating==='again'?3:8;
      // Repeat only after enough intervening cards; small pools wait for the next pass.
      if(rating!=='good'&&queue.length-position-1>=distance)queue.splice(position+distance+1,0,q.id);
    }
    const due=new Date(result.state.due_at).toLocaleDateString(undefined,{month:'short',day:'numeric'});
    status(`${names[mode]} · Marked ${rating}. ${rating==='again'?'Added to Weak; due again shortly.':`Next review ${due}.`}`);
    position++;renderQuestion();
  }catch{status('Rating could not be saved. Please try again; this question has not advanced.');for(const b of document.querySelectorAll('[data-rating]'))b.disabled=false;}
  finally{loading=false;}
}
async function navigate(delta) {if(loading||!current())return;try{await saveDraft();position=Math.max(0,position+delta);renderQuestion();}catch{status('Your response could not be saved. Try again before leaving this question.');}}
async function changeMode(next) {if(loading)return;mode=next;$('search').value='';for(const button of document.querySelectorAll('[data-mode]')){if(button.dataset.mode===next)button.setAttribute('aria-current','page');else button.removeAttribute('aria-current');}await load();}
$('reveal').addEventListener('click',revealAll);
$('next').addEventListener('click',()=>navigate(1));$('previous').addEventListener('click',()=>navigate(-1));
for(const button of document.querySelectorAll('[data-rating]'))button.addEventListener('click',()=>rate(button.dataset.rating));
for(const button of document.querySelectorAll('[data-mode]'))button.addEventListener('click',()=>changeMode(button.dataset.mode));
$('back-learn').addEventListener('click',()=>changeMode('learn'));
$('chapter').addEventListener('change',()=>{updatePages();load();});$('subject').addEventListener('change',()=>{updateSubjects();load();});$('page').addEventListener('change',load);
$('search').addEventListener('input',()=>{clearTimeout(searchTimer);searchTimer=setTimeout(load,300);});
$('clear-search').addEventListener('click',()=>{$('search').value='';load();});
$('bookmark').addEventListener('click',async()=>{const q=current();if(!q)return;try{await write(q.id,{bookmarked:!states[q.id]?.bookmarked});if(current()?.id===q.id){$('bookmark').setAttribute('aria-pressed',String(states[q.id].bookmarked));$('bookmark').textContent=states[q.id].bookmarked?'★ Bookmarked':'☆ Bookmark';}}catch{status('Bookmark could not be saved. Try again.');}});
$('history').addEventListener('click',async()=>{
  const q=current();if(!q)return;const target=$('history-content');if(!target.hidden){target.hidden=true;return;}
  try{const result=await api(`/api/history/${encodeURIComponent(q.id)}`);if(current()?.id!==q.id)return;target.replaceChildren(el('p',result.attempts.length?'Previous recall attempts':'No rated attempts yet.'));
    for(const attempt of result.attempts){const details=el('details');details.append(el('summary',`${new Date(attempt.attempted_at).toLocaleString()} · ${attempt.rating} · revision ${attempt.revision}`));const response=typeof attempt.response==='string'?attempt.response:Object.values(attempt.response).join(' / ');details.append(el('pre',response||'(No written response)'));target.append(details);}target.hidden=false;
  }catch{status('Unable to load attempt history.');}
});
function setTheme(theme){document.documentElement.dataset.theme=theme;$('theme').textContent=theme==='dark'?'Light mode':'Dark mode';try{localStorage.setItem('workbook-theme',theme);}catch{}}
let theme='light';try{theme=localStorage.getItem('workbook-theme')||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');}catch{}setTheme(theme);
$('theme').addEventListener('click',()=>setTheme(document.documentElement.dataset.theme==='dark'?'light':'dark'));
window.addEventListener('pagehide',()=>{clearTimeout(draftTimer);const q=current();if(q)fetch(`/api/progress/${encodeURIComponent(q.id)}`,{method:'POST',keepalive:true,headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify({draft:draft()})}).catch(()=>{});});
updateSubjects();load();
