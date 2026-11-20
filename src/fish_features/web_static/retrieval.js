(() => {
  const el=id=>document.getElementById(id);
  const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const labels={hsv:'HSV toàn cục',spatial_hsv:'HSV theo vùng',color_moments:'Color Moment',geometry:'Hình học',fourier:'Fourier',contour_profile:'Contour Profile',glcm:'GLCM',ulbp:'Uniform LBP'};
  const pct=n=>(100*n).toLocaleString('vi-VN',{maximumFractionDigits:2})+'%';
  const dec=n=>Number(n).toLocaleString('vi-VN',{maximumFractionDigits:6});
  let result=null,busy=false;
  function download(data,name){
    const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));
    const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  async function get(url){const r=await fetch(url),d=await r.json();if(!r.ok)throw Error(d.error||'Không tải được dữ liệu');return d;}
  async function runSearch(id){
    if(busy)return;
    const file=el('query-file').files[0];
    if(!id&&!file)return;
    busy=true;el('search-submit').disabled=true;el('search-submit').textContent='Đang trích rút và tìm kiếm…';
    el('query-message').hidden=false;el('query-message').className='loading';el('query-message').textContent=(!id&&el('remove-background').checked)?'Đang tách nền bằng RMBG-2.0 trên máy local, sau đó trích rút và tìm kiếm. Lần đầu tải/nạp model có thể lâu…':'Đang xử lý ảnh, tính đặc trưng và so sánh với gallery…';
    el('search-results').innerHTML='';result=null;
    el('search-section').scrollIntoView({behavior:'smooth',block:'start'});
    try{
      if(file&&!id&&file.size>10*1024*1024)throw Error('Ảnh vượt giới hạn 10 MiB.');
      const params=new URLSearchParams(id?{id:String(id)}:{filename:file.name,flip:el('flip-query').checked?'1':'0',background:el('remove-background').checked?'rmbg2':'none'});
      const response=await fetch('/api/search?'+params,{method:'POST',body:id?undefined:file,headers:id?{}:{'Content-Type':'application/octet-stream'}});
      const data=await response.json();if(!response.ok)throw Error(data.error||'Không tìm kiếm được');
      result=data;renderResult(data);
      el('query-message').hidden=true;
    }catch(error){el('query-message').className='error';el('query-message').textContent=error.message;}
    finally{busy=false;el('search-submit').disabled=false;el('search-submit').textContent='Tìm 5 ảnh tương đồng';backgroundStatus();}
  }
  function renderResult(data){
    const q=data.query;
    el('search-results').innerHTML=`<div class="query-summary"><div class="section-title"><div><p class="eyebrow">ẢNH ĐÃ XỬ LÝ</p><h3>${escape(q.path)}</h3></div><button id="download-search" class="secondary">Tải toàn bộ kết quả JSON</button></div>
      <div class="preview-grid">${Object.entries(data.previews).map(([kind,src])=>`<figure><img src="${src}" alt="${escape(kind)}"><figcaption>${{uploaded:'Ảnh upload trước tách nền',rmbg_alpha:'Alpha matte từ RMBG-2.0',original:'Ảnh nền trắng trên canvas chuẩn',mask:'Mặt nạ dùng trích rút đặc trưng',contour:'Đường bao và bounding box'}[kind]}</figcaption></figure>`).join('')}</div>
      ${data.preparation.background_removal?.applied?`<p class="muted">Đã tách nền bằng ${escape(data.preparation.background_removal.model_id)} · Đầu vào model 1024 × 1024 · Thiết bị ${escape(data.preparation.background_removal.device)} · ${dec(data.preparation.background_removal.elapsed_ms)} ms. Alpha matte ghép trên nền trắng trước khi đưa về canvas chuẩn.</p>`:''}
      <p class="muted">${data.gallery_count} ảnh gallery · ${data.candidate_count} ứng viên · Loại ${data.excluded_identical} ảnh trùng pixel với truy vấn · Chuẩn bị & trích rút: ${dec(data.timing_ms.prepare_extract_and_index)} ms · Xếp hạng: ${dec(data.timing_ms.ranking)} ms</p>
      ${q.metadata.warnings.length?`<div class="error">Cảnh báo phân đoạn: ${q.metadata.warnings.map(escape).join(', ')}. Hãy kiểm tra mặt nạ trước khi diễn giải kết quả.</div>`:''}
      ${data.preparation.letterboxed?'<p class="muted">Ảnh đã được co giãn giữ tỉ lệ và đặt giữa canvas trắng 640 × 320.</p>':''}
      </div>
      <div class="section-title result-title"><div><p class="eyebrow">KẾT QUẢ TRUY HỒI</p><h2>5 ảnh tương đồng nhất</h2></div><span class="muted">Xếp giảm dần theo S = 1 − D</span></div>
      <p class="muted">Điểm S thể hiện độ gần theo cấu hình đang dùng, không phải xác suất cùng loài hay phần trăm giống nhau. Tên loài bên dưới là nhãn có sẵn của ảnh kết quả.</p>
      <div class="result-grid">${data.results.map(r=>`<article class="result-card"><div class="result-rank">Hạng ${r.rank}<strong>S = ${dec(r.similarity)}</strong></div><button class="result-image" data-id="${r.image_id}" aria-label="Xem chi tiết ${escape(r.path)}"><img src="/media/${r.image_id}" alt="${escape(r.species_name)}"><span>${escape(r.species_name||'Chưa có nhãn')}</span></button><p class="result-file">${escape(r.path)}</p><div class="score-track"><span style="width:${r.similarity*100}%"></span></div><p class="muted">D = ${dec(r.distance)}</p><details><summary>Giải thích điểm</summary><table><thead><tr><th>Nhóm</th><th>d</th><th>w × d</th></tr></thead><tbody>${Object.entries(r.components).map(([k,c])=>`<tr><td>${labels[k]}</td><td>${dec(c.distance)}</td><td>${dec(c.contribution)}</td></tr>`).join('')}</tbody></table><p class="muted">Tổng w × d = ${dec(r.distance)}</p></details></article>`).join('')}</div>
      ${data.results.length<5?'<p class="error">Gallery hiện có ít hơn 5 ứng viên hợp lệ.</p>':''}
      <section class="feature-panel"><h3>Đối chiếu các giá trị trung gian</h3><p class="muted">Chọn nhóm để xem vector truy vấn và vector của từng kết quả. Các khoảng cách và phần đóng góp phía trên được tính từ các vector này.</p><label class="compare-label">Nhóm đặc trưng<select id="compare-group">${Object.entries(labels).map(([k,l])=>`<option value="${k}">${l} · ${q.features[k].length} chiều</option>`).join('')}</select></label><div id="compare-values"></div></section>
      <details class="feature-panel"><summary>Cấu hình, thống kê chuẩn hóa gallery & dữ liệu truy vấn</summary><pre>${escape(JSON.stringify({profile:data.profile,feature_config:data.feature_config,dimensions:data.dimensions,preparation:data.preparation,query_metadata:q.metadata,gallery_fingerprint:data.gallery_fingerprint,normalizers:data.normalizers},null,2))}</pre></details>`;
    el('download-search').onclick=()=>download(data,'fish-search-result.json');
    el('search-results').querySelectorAll('[data-id]').forEach(button=>button.onclick=()=>window.openDetail(button.dataset.id));
    el('compare-group').onchange=renderCompare;renderCompare();
  }
  function renderCompare(){
    const key=el('compare-group').value;
    const vectors=[['Ảnh truy vấn',result.query.features[key]],...result.results.map(r=>['Hạng '+r.rank,r.features[key]])];
    el('compare-values').innerHTML=vectors.map(([name,vector])=>`<details><summary>${name} · ${vector.length} giá trị</summary><pre>${escape(JSON.stringify(vector,null,2))}</pre></details>`).join('');
  }
  async function settings(){
    try{
      const profile=await get('/api/retrieval-config');
      el('retrieval-config').innerHTML=`<h3>Cấu hình đang chạy: ${escape(profile.version)}</h3><p class="muted">Cấu hình trích rút: <code>${escape(profile.feature_config_id)}</code><br>Top K = 5 · Tự loại ảnh trùng pixel · Không lọc theo nhãn loài</p><div class="weight-grid">${Object.entries(profile.weights).map(([k,w])=>`<div><span>${labels[k]}</span><strong>${pct(w)}</strong></div>`).join('')}</div><p class="muted">HSV và LBP: Hellinger. Spatial HSV: trung bình Hellinger các vùng. GLCM, hình học, Fourier, Color Moment: RMS sau chuẩn hóa bằng độ lệch chuẩn gallery, rồi d = r / (1 + r). Contour Profile: RMS của profile đã chuẩn hóa, rồi d = r / (1 + r). D = Σw × d; S = 1 − D.</p><details><summary>Xem toàn bộ cấu hình</summary><pre>${escape(JSON.stringify(profile,null,2))}</pre></details>`;
    }catch(error){el('retrieval-config').textContent=error.message;}
    try{
      const report=await get('/api/evaluation'), m=report.test.selected, counts=report.split_counts;
      el('evaluation-summary').innerHTML=`<h3>Đánh giá trên tập test tách biệt</h3><p class="muted">Seed 42 · Gallery ${counts.gallery} ảnh · Validation ${counts.validation} ảnh · Test ${counts.test} ảnh. Trọng số chọn theo mAP@5 trên validation, không chọn bằng test.</p><div class="evaluation-metrics">${[['Precision@5',m.precision_at_5],['Recall@5',m.recall_at_5],['Hit@5',m.hit_at_5],['mAP@5',m.ap_at_5],['nDCG@5',m.ndcg_at_5]].map(([label,value])=>`<div class="metric"><span>${label}</span><strong>${dec(value)}</strong></div>`).join('')}</div><p class="muted">Relevant = cùng mã loài trong tên file. Đây là phép đo thay thế, không phải nhãn tương đồng thị giác do người đánh giá. Khi chạy web, gallery sử dụng đủ 1.000 ảnh; số liệu test ở đây sử dụng gallery 530 ảnh theo protocol holdout.</p><p id="evaluation-profile-note" class="muted"></p><details><summary>So sánh nhóm đặc trưng trên test</summary><div class="table-wrap"><table><thead><tr><th>Phương án</th><th>P@5</th><th>Hit@5</th><th>mAP@5</th></tr></thead><tbody>${Object.entries(report.test).map(([name,v])=>`<tr><td>${escape(name)}</td><td>${dec(v.precision_at_5)}</td><td>${dec(v.hit_at_5)}</td><td>${dec(v.ap_at_5)}</td></tr>`).join('')}</tbody></table></div></details><button id="download-evaluation" class="secondary">Tải báo cáo đánh giá JSON</button>`;
      el('download-evaluation').onclick=()=>download(report,'fish-evaluation.json');
      const profile=await get('/api/retrieval-config');
      const same=Object.keys(labels).every(k=>Math.abs(profile.weights[k]-report.selected_profile.weights[k])<1e-12);
      el('evaluation-profile-note').textContent=same?'Trọng số đang chạy khớp phương án đã đánh giá.':'Lưu ý: trọng số hiện tại khác phương án trong báo cáo; cần chạy đánh giá lại trước khi dùng các số liệu này cho cấu hình mới.';
    }catch(error){el('evaluation-summary').textContent=error.message;}
  }
  async function backgroundStatus(){
    try{
      const data=await get('/api/background-status');
      el('background-status').textContent='RMBG-2.0: '+data.message;
      el('background-status').dataset.state=data.state;
    }catch(error){el('background-status').textContent='Không kiểm tra được RMBG-2.0: '+error.message;}
  }
  el('query-form').onsubmit=e=>{e.preventDefault();runSearch();};
  document.addEventListener('search-dataset',e=>runSearch(e.detail));
  settings();
  backgroundStatus();
})();
