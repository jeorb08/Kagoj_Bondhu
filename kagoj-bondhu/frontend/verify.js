/* Adds Verify beside the original four modules. No persisted case data. */
const vs={conf:{},readMode:'none',confirmed:false,epoch:0,module:'payslip',image:null,values:{},result:null,busy:false,reference:null,label:'',error:''};
const VF={payslip:['name','emp_id','basic','house','medical','transport','food','ot_hours','ot_rate','ot_amount','deduction','net'],loan:['name','principal','flat','months','inst','total'],bill:['name','meter','units','energy','demand','vat','misc','total']};
const fieldLabels={name:['Name','নাম'],emp_id:['Employee ID','কর্মী আইডি'],basic:['Basic wage','মূল মজুরি'],house:['House rent','বাড়ি ভাড়া'],medical:['Medical','চিকিৎসা'],transport:['Transport','যাতায়াত'],food:['Food','খাদ্য'],ot_hours:['OT hours','ওভারটাইম ঘণ্টা'],ot_rate:['Printed OT rate','ছাপানো ওভারটাইম হার'],ot_amount:['OT amount','ওভারটাইম টাকা'],deduction:['Deduction','কর্তন'],net:['Net pay','নিট বেতন'],principal:['Principal','ঋণের আসল'],flat:['Annual flat rate (%)','বার্ষিক ফ্ল্যাট হার (%)'],months:['Months','মাস'],inst:['Monthly installment','মাসিক কিস্তি'],total:['Total','মোট'],meter:['Meter ID','মিটার আইডি'],units:['Units','ইউনিট'],energy:['Energy charge','এনার্জি চার্জ'],demand:['Demand charge','ডিমান্ড চার্জ'],vat:['VAT amount','ভ্যাটের টাকা'],misc:['Other charges','অন্যান্য চার্জ']};
const isText=k=>['name','emp_id','meter'].includes(k);
function verifyView(){
 const r=vs.result;
 return `<main class="wrap"><div class="mod-top"><button class="back" data-act="home">${L('Back','পেছনে')}</button><h2>🔎 ${L('Kagoj Bondhu Verify','কাগজ বন্ধু Verify')}</h2><p>${L('Evidence for a human reviewer. No automatic rejection.','মানুষের পর্যালোচনার জন্য তথ্য। স্বয়ংক্রিয় প্রত্যাখ্যান নয়।')}</p></div>
 <div class="actions"><button class="btn ghost" id="vcompare">${L("Compare two documents","দুটি কাগজ তুলনা করুন")}</button>${['consistent','edited','blurry'].map((id,i)=>`<button class="btn ghost" data-vsample="${id}" ${vs.busy?'disabled':''}>${L(['Consistent sample','Edited sample','Blurry sample'][i],['মিল আছে এমন নমুনা','সম্পাদিত নমুনা','অস্পষ্ট নমুনা'][i])}</button>`).join('')}<button class="btn ghost" id="vclear">${L('Clear case','কেস মুছুন')}</button></div>
 <p class="fine">${L('Upload a document to read its fields with AI, then confirm them. Sample buttons load labelled demo fields; Read with AI also works on samples.','কাগজ আপলোড করলে এআই তথ্য পড়বে, তারপর মিলিয়ে নিশ্চিত করুন। নমুনা বাটনে ডেমো তথ্য আসে; নমুনাতেও এআই দিয়ে পড়তে পারেন।')}</p>
 <div class="stage"><section class="pane-doc"><label class="drop"><input type="file" id="vfile" ${vs.busy?'disabled':''} accept="image/jpeg,image/png,image/webp" hidden><b>📷 ${L('Upload synthetic document','কৃত্রিম কাগজ আপলোড করুন')}</b></label>
 ${vs.image?`<div style="position:relative;margin-top:16px;line-height:0"><img src="${vs.image}" alt="Document being reviewed" style="width:100%;display:block">${(r?.regions||[]).map(b=>`<span title="Model signal, not proof" style="position:absolute;left:${b.x*100}%;top:${b.y*100}%;width:${b.width*100}%;height:${b.height*100}%;border:3px solid #c13630;border-radius:50%;background:#ff000022"></span>`).join('')}</div><p class="fine">${esc(vs.label)} ${L('Red rings show model signals, not confirmed edits.','লাল বৃত্ত মডেলের সংকেত, নিশ্চিত সম্পাদনা নয়।')}</p>`:''}
 </section><section class="side"><h3>${L('Confirm the printed fields','ছাপানো তথ্য নিশ্চিত করুন')}</h3>
 <label class="fld"><span>${L('Document type','কাগজের ধরন')}</span><select id="vmodule" ${vs.busy?'disabled':''}>${Object.keys(VF).map(k=>`<option ${vs.module===k?'selected':''}>${k}</option>`).join('')}</select></label>
 <div class="actions"><button class="btn ghost" id="vread" ${vs.busy||!vs.image?'disabled':''}>${vs.busy?L('Working…','কাজ হচ্ছে…'):L('Read with AI','এআই দিয়ে পড়ুন')}</button></div>
 <p class="fine">${vs.readMode==='live'?L('AI extracted these fields. Confidence is uncalibrated; confirm every field.','এআই এই তথ্য পড়েছে। আত্মবিশ্বাস পরীক্ষিত নয়; প্রতিটি তথ্য মিলিয়ে দেখুন।'):vs.readMode==='sample'?L('Known sample fields; not AI extraction.','পরিচিত নমুনার তথ্য; এআই দিয়ে পড়া নয়।'):vs.readMode==='cannot_assess'?L('Image is unclear; retake or run the quality check.','ছবি অস্পষ্ট; আবার তুলুন বা ছবির মান পরীক্ষা করুন।'):L('Fields may also be entered manually. No values are guessed when AI is unavailable.','তথ্য হাতে লিখতেও পারেন। এআই অনুপলব্ধ হলে কোনো মান অনুমান করা হয় না।')}</p>
 <div class="box grid2">${VF[vs.module].map(k=>`<label class="fld"><span>${L(...fieldLabels[k])}${vs.conf[k]!==undefined?` <small>${L('Reader confidence','পড়ার আত্মবিশ্বাস')}: ${N(Math.round(vs.conf[k]*100))}%</small>`:''}</span><span class="inp"><input ${isText(k)?'type="text" maxlength="160"':'type="number" min="0" step="any"'} data-vfield="${k}" value="${esc(vs.values[k]??'')}"></span></label>`).join('')}</div>
 <p class="fine">${L('For unreadable images, leave the values empty and run the quality check.','অস্পষ্ট ছবিতে তথ্য ফাঁকা রেখে ছবির মান পরীক্ষা করুন।')}</p>
 <label><input type="checkbox" id="vconfirmed" ${vs.confirmed?'checked':''}> ${L('I checked these fields against the image','ছবির সঙ্গে তথ্যগুলো মিলিয়েছি')}</label>
 <div class="actions"><button class="btn primary" id="vrun" ${vs.busy||!vs.image?'disabled':''}>${vs.busy?L('Checking…','যাচাই হচ্ছে…'):L('Check evidence','তথ্য যাচাই করুন')}</button><button class="btn ghost" id="vreference" ${!vs.image?'disabled':''}>${L('Use as reference','নমুনা হিসেবে রাখুন')}</button></div>
 <p class="fine">${vs.reference?L('One reference held in this tab. Clear case removes it.','এই ট্যাবে একটি নমুনা আছে। কেস মুছলে সেটিও মুছবে।'):L('Optional reference comparison; no cross-user case database.','ঐচ্ছিক নমুনা তুলনা; অন্য ব্যবহারকারীর কেস রাখা হয় না।')}</p>
 ${vs.error?`<p role="alert" class="sim">${esc(vs.error)}</p>`:''}
 ${r?`<div id="vresult"><div class="verdict tone-${r.outcome==='needs_review'?'bad':r.outcome==='cannot_assess'?'warn':'good'}"><div class="v-head">${esc(r.label[state.lang])}</div><p class="fine">${r.explanation?.mode==='ai'?L('AI explanation · evidence and numbers constrained by code','এআই ব্যাখ্যা · তথ্য ও সংখ্যা কোডের সীমার মধ্যে'):L('Rule-based explanation · AI unavailable or disabled','নিয়মভিত্তিক ব্যাখ্যা · এআই অনুপলব্ধ বা বন্ধ')}</p><p>${esc(r.explanation?.[state.lang]||r.summary[state.lang])}</p>${r.missing.length?`<p>${L('Missing or unconfirmed','অনুপস্থিত বা নিশ্চিত নয়')}: ${esc(r.missing.join(', '))}</p>`:''}<p class="fine">${L('No authenticity certification; a person makes the next decision.','এটি সত্যতার সনদ নয়; পরের সিদ্ধান্ত মানুষ নেবেন।')}</p></div>
 <div class="box">${r.findings.map(f=>`<p><b>${esc(f.code)}</b><br>${esc(f[state.lang])}</p>`).join('')||L('No finding in the completed checks.','সম্পন্ন পরীক্ষায় কোনো অমিল পাওয়া যায়নি।')}</div>
 <details class="box"><summary>${L('Technical evidence','পরীক্ষার তথ্য')}</summary><pre style="white-space:pre-wrap">${esc(JSON.stringify({quality:r.quality,ml:r.ml},null,2))}</pre></details>
 <div class="actions"><button class="btn ghost" id="vdraft">${L('Draft re-upload request','আবার ছবি চাওয়ার খসড়া')}</button><button class="btn ghost" id="vdownload">${L('Download report','রিপোর্ট ডাউনলোড')}</button><button class="btn ghost" id="vlisten">${L('Listen','শুনুন')}</button></div><div id="vdraftbox" class="box" hidden></div></div>`:''}
 </section></div></main>`;
}
async function loadVSample(id){
 if(vs.busy)return;
 const epoch=++vs.epoch;
 vs.busy=true;vs.error='';render();
 try{const r=await fetch('/api/verify/sample/'+id);if(!r.ok)throw Error('Sample unavailable');const j=await r.json();if(epoch!==vs.epoch)return;Object.assign(vs,{module:j.module,image:j.image,values:j.values,result:null,label:j.label,conf:{},confirmed:false,readMode:'sample'});}
 catch(e){if(epoch===vs.epoch)vs.error=e.message}finally{if(epoch===vs.epoch){vs.busy=false;render()}}
}
async function runVerify(){
 if(vs.busy||!vs.image)return;
 const epoch=++vs.epoch,confirmed=vs.confirmed;
 const payload={module:vs.module,image:vs.image,values:{...vs.values},confirmed,reference_image:vs.reference?.image,reference_values:vs.reference?.values};
 vs.busy=true;vs.error='';render();
 try{const r=await fetch('/api/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const j=await r.json();if(!r.ok)throw Error(typeof j.detail==='string'?j.detail:'Please check input values');if(epoch!==vs.epoch||JSON.stringify(payload.values)!==JSON.stringify(vs.values)||payload.module!==vs.module||payload.image!==vs.image)return;vs.result=j}
 catch(e){if(epoch===vs.epoch)vs.error=e.message}finally{if(epoch===vs.epoch){vs.busy=false;render()}}
}
function ledgerEditor(){return `<details class="box"><summary>${L('Edit names, dates and payment types','নাম, তারিখ ও জমার ধরন সম্পাদনা')}</summary><label>${L('Assessment date','হিসাবের তারিখ')} <input type="date" id="kasof" value="${esc(state.asOf||TODAY)}"></label>${KH.map((e,i)=>`<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px"><input aria-label="Name" data-kname="${i}" value="${esc(e[1])}" maxlength="160"><input aria-label="Date" type="date" data-kdate="${i}" value="${esc(e[0])}"><select aria-label="Entry type" data-kkind="${i}"><option value="b" ${e[4]==='b'?'selected':''}>${L('Credit','বাকি')}</option><option value="p" ${e[4]==='p'?'selected':''}>${L('Payment','জমা')}</option></select></div>`).join('')}</details>`}
document.addEventListener('input',e=>{
 if(e.target.dataset.vfield){vs.values[e.target.dataset.vfield]=e.target.value;vs.result=null;vs.confirmed=false;$('#vresult')?.remove();if($('#vconfirmed'))$('#vconfirmed').checked=false}
 for(const [key,idx] of [['kname',1],['kdate',0],['kkind',4]])if(e.target.dataset[key]!==undefined){KH[+e.target.dataset[key]][idx]=e.target.value;state.checked=null}
 if(e.target.id==='kasof'){state.asOf=e.target.value;state.checked=null}
});
document.addEventListener('change',e=>{
 if(e.target.id==='vconfirmed'){vs.confirmed=e.target.checked}
 if(e.target.id==='vmodule'){vs.epoch++;vs.module=e.target.value;vs.values={};vs.conf={};vs.readMode='none';vs.confirmed=false;vs.result=null;render()}
 if(e.target.id==='vfile'){
  const f=e.target.files[0];if(!f)return;
  if(f.size>6*1024*1024){toast('Maximum 6 MB');return}
  // Preserve original JPEG traces for forensic signals; do not re-compress Verify uploads.
  const rd=new FileReader();rd.onload=()=>{Object.assign(vs,{image:rd.result,label:f.name,values:{},conf:{},readMode:'none',confirmed:false,result:null,error:''});render();readVerifyAI()};rd.readAsDataURL(f);
 }
});
document.addEventListener('click',e=>{
 const a=e.target.closest('button');if(!a)return;
 if(a.dataset.vsample)loadVSample(a.dataset.vsample);
 if(a.id==='vcompare'){state.view='compare';stopSpeech();render()}
 if(a.id==='vrun')runVerify();
 if(a.id==='vread')readVerifyAI();
 if(a.id==='vreference'){vs.reference={image:vs.image,values:{...vs.values}};toast(L('Reference held in this tab.','এই ট্যাবে নমুনা রাখা হয়েছে।'))}
 if(a.id==='vclear'){vs.epoch++;Object.assign(vs,{busy:false,image:null,reference:null,result:null,values:{},conf:{},confirmed:false,readMode:'none',error:'',label:''});stopSpeech();render()}
 if(a.id==='vdraft'&&vs.result){$('#vdraftbox').hidden=false;$('#vdraftbox').textContent=vs.result.reupload_draft+' '+L('(Draft only; nothing sent.)','(শুধু খসড়া; কিছু পাঠানো হয়নি।)')}
 if(a.id==='vlisten'&&vs.result)speak(vs.result.explanation?.[state.lang]||vs.result.summary[state.lang]);
 if(a.id==='vdownload'&&vs.result){const url=URL.createObjectURL(new Blob([JSON.stringify(vs.result,null,2)],{type:'application/json'}));const link=document.createElement('a');link.href=url;link.download='kagoj-bondhu-review.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
});

async function readVerifyAI(){
 if(vs.busy||!vs.image)return;
 const epoch=++vs.epoch,module=vs.module,image=vs.image;
 vs.busy=true;vs.error='';vs.result=null;vs.values={};vs.conf={};vs.confirmed=false;vs.readMode='loading';render();
 try{
  const r=await fetch('/api/verify/read',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({module,image})});
  const j=await r.json();if(!r.ok)throw new Error(typeof j.detail==='string'?j.detail:'AI reading failed');
  if(epoch!==vs.epoch)return;
  if(j.mode==='cannot_assess'){vs.readMode='cannot_assess';vs.error=L('Photo is too unclear. Please retake it.','ছবিটি অস্পষ্ট। আবার তুলুন।')}
  else{for(const [key,f] of Object.entries(j.fields||{})){vs.values[key]=f.value;vs.conf[key]=f.confidence;}vs.readMode='live';}
 }catch(e){if(epoch===vs.epoch){vs.readMode='unavailable';vs.error=e.message}}
 finally{if(epoch===vs.epoch){vs.busy=false;render()}}
}
