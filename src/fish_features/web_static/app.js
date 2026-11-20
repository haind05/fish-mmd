const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number = n => Number(n).toLocaleString('vi-VN');
const decimal = n => Number(n).toLocaleString('vi-VN', {maximumFractionDigits:6});
const groups = {
  glcm:['GLCM · Kết cấu', 'ASM, Contrast, Homogeneity, Correlation, Entropy; lần lượt theo từng độ dời.'],
  ulbp:['Uniform LBP · Kết cấu cục bộ', '58 mã uniform giữ hướng và một nhóm non-uniform. Histogram chuẩn hóa L1.'],
  geometry:['Hình học tổng thể', 'Aspect Ratio, Solidity và Extent; mỗi thành phần có thang giá trị riêng.'],
  contour_profile:['Contour Profile · Đường bao', 'Khoảng cách từ các điểm mẫu đến trọng tâm mask, chia khoảng cách trung bình.'],
  fourier:['Fourier Descriptor · Hình dạng', 'Biên độ D2 trở đi, chuẩn hóa theo |F1|.'],
  hsv:['HSV Histogram · Màu toàn cục', 'Thứ tự bin: V thay đổi nhanh nhất, sau đó S và H. Tổng histogram bằng 1.'],
  color_moments:['Color Moment · Thống kê RGB', 'Mean R/G/B, độ lệch chuẩn R/G/B, căn bậc ba có dấu của moment trung tâm bậc ba R/G/B.'],
  spatial_hsv:['Spatial HSV · Màu theo vùng', 'Histogram riêng từng ô, duyệt trái sang phải rồi trên xuống dưới trên bounding box.']
};
let page=1, pages=1, galleryRequest=0, detailRequest=0, current=null, feature=null;

async function api(url){
  const response=await fetch(url);
  const result=await response.json();
  if(!response.ok) throw new Error(result.error || 'Không tải được dữ liệu.');
  return result;
}
function notice(message){$('notice').hidden=!message;$('notice').textContent=message || '';}

async function refresh(){
  notice('');$('refresh').disabled=true;
  try{
    const data=await api('/api/overview');
    $('images-count').textContent=number(data.images);
    $('species-count').textContent=number(data.species);
    $('features-count').textContent=number(data.feature_sets);
    $('db-status').textContent='Đã kết nối';
    const selected=$('species').value;
    $('species').innerHTML='<option value="">Tất cả loài</option>'+data.species_options.filter(s=>s.species_code!==null).map(s=>`<option value="${s.species_code}">${esc(s.species_name)} (${s.count})</option>`).join('');
    $('species').value=selected;
    await loadGallery();
  }catch(error){notice(error.message);$('db-status').textContent='Chưa kết nối';$('grid').innerHTML='<div class="empty">Hãy khởi động CSDL rồi bấm Làm mới dữ liệu.</div>';}
  finally{$('refresh').disabled=false;}
}
async function loadGallery(){
  const request=++galleryRequest;
  $('grid').innerHTML='<div class="empty">Đang tải ảnh từ CSDL…</div>';
  $('previous').disabled=true;$('next').disabled=true;
  try{
    const query=new URLSearchParams({page,q:$('search').value,species:$('species').value});
    const data=await api('/api/images?'+query);
    if(request!==galleryRequest)return;
    page=data.page;pages=data.pages;
    $('result-count').textContent=`${number(data.total)} ảnh`;
    $('grid').innerHTML=data.items.length ? data.items.map(i=>`<button class="card" data-id="${i.image_id}" aria-label="Xem ${esc(i.species_name || i.relative_path)}"><img loading="lazy" src="/media/${i.image_id}" alt="${esc(i.species_name || 'Ảnh cá')}"><span class="card-copy"><span class="species-name">${esc(i.species_name || 'Chưa có tên loài')}</span><span class="filename" title="${esc(i.relative_path)}">${esc(i.relative_path)}</span><span class="card-meta"><span>${i.width} × ${i.height} px</span><span class="badge">${i.feature_count ? 'Có đặc trưng' : 'Chưa trích rút'}</span></span></span></button>`).join('') : '<div class="empty">Không tìm thấy ảnh phù hợp. Hãy thử tên khác hoặc chọn tất cả loài.</div>';
    $('page-label').textContent=`Trang ${page} / ${pages}`;
    $('previous').disabled=page<=1;$('next').disabled=page>=pages;
    $('grid').querySelectorAll('.card').forEach(card=>card.onclick=()=>openDetail(card.dataset.id));
    $('grid').querySelectorAll('img').forEach(img=>img.onerror=()=>{img.alt='Không tìm thấy file ảnh trong data/images';});
  }catch(error){if(request===galleryRequest){notice(error.message);$('grid').innerHTML='<div class="empty">Không tải được thư viện ảnh.</div>';}}
}
async function openDetail(id){
  const request=++detailRequest;
  $('detail-title').textContent='Đang tải…';$('detail-body').innerHTML='<div class="loading">Đang đọc các đặc trưng từ CSDL…</div>';
  if(!$('detail').open)$('detail').showModal();
  try{
    const data=await api('/api/images/'+id);
    if(request!==detailRequest || !$('detail').open)return;
    current=data;
    $('detail-title').textContent=data.image.species_name || 'Chi tiết ảnh';
    renderDetail(0);
  }catch(error){if(request===detailRequest)$('detail-body').innerHTML=`<div class="error">${esc(error.message)}</div>`;}
}
function renderDetail(index){
  feature=current.features[index];
  const img=current.image;
  const previews=[['original','Ảnh gốc'],['mask','Mặt nạ vùng cá'],['contour','Đường bao & bounding box']];
  const config=feature ? '&config='+feature.config_id : '';
  $('detail-body').innerHTML=`<p class="detail-file">${esc(img.relative_path)} · ${img.width} × ${img.height} px · ID ${img.image_id}</p>
  <div class="preview-grid">${previews.map(([key,title])=>`<figure><img src="/media/${img.image_id}?kind=${key}${config}" alt="${title}"><figcaption>${title}</figcaption></figure>`).join('')}</div>
  <p class="muted">Mặt nạ và đường bao được dựng lại từ ảnh gốc theo ngưỡng của cấu hình đang chọn. Các vector bên dưới là dữ liệu đã lưu trong CSDL.</p>
  ${!feature ? '<div class="error">Ảnh này chưa có bộ đặc trưng hợp lệ trong CSDL.</div>' : `
  <div class="detail-toolbar"><label>Cấu hình trích rút<select id="config-choice">${current.features.map((f,i)=>`<option value="${i}" ${i===index?'selected':''}>${esc(f.parameters.algorithm_version)} · ${f.config_id.slice(0,12)} · ${new Date(f.extracted_at).toLocaleString('vi-VN')}</option>`).join('')}</select></label><button id="download" class="secondary">Tải dữ liệu JSON</button></div>
  <div class="metrics">${[['Aspect Ratio',feature.geometry[0]],['Solidity',feature.geometry[1]],['Extent',feature.geometry[2]],['Diện tích mask',feature.metadata.area]].map(([label,value])=>`<div class="metric"><span>${label}</span><strong>${decimal(value)}</strong></div>`).join('')}</div>
  ${feature.metadata.warnings.length ? `<div class="error">Cần kiểm tra: ${feature.metadata.warnings.map(esc).join(', ')}</div>` : ''}
  <section class="feature-panel"><div class="feature-controls"><h3 style="margin:0">Giá trị đặc trưng</h3><select id="feature-choice" aria-label="Chọn nhóm đặc trưng">${Object.entries(groups).map(([key,[title]])=>`<option value="${key}">${title} · ${feature[key].length} chiều</option>`).join('')}</select></div><p id="feature-description" class="muted"></p><div id="chart"></div><p class="muted">Biểu đồ tự điều chỉnh trục theo nhóm đang xem; không dùng chiều cao cột để so sánh giữa các nhóm.</p><details><summary>Xem toàn bộ giá trị</summary><div class="table-wrap"><table><thead><tr><th>Thành phần</th><th>Giá trị</th></tr></thead><tbody id="vector-table"></tbody></table></div></details></section>
  <details class="feature-panel"><summary>Thông tin phân đoạn & kiểm tra</summary><pre>${esc(JSON.stringify(feature.metadata,null,2))}</pre></details>
  <details class="feature-panel"><summary>Tham số thuật toán & số chiều</summary><pre>${esc(JSON.stringify({config_id:feature.config_id,parameters:feature.parameters,dimensions:feature.dimensions},null,2))}</pre></details>`}`;
  $('detail-body').querySelectorAll('img').forEach(el=>el.onerror=()=>el.alt='Không tải được ảnh. Kiểm tra thư mục data/images.');
  if(feature){
    $('config-choice').onchange=e=>renderDetail(Number(e.target.value));
    $('feature-choice').onchange=drawFeature;
    $('download').onclick=()=>{
      const blob=new Blob([JSON.stringify({image:current.image,feature},null,2)],{type:'application/json'});
      const link=document.createElement('a');const url=URL.createObjectURL(blob);
      link.href=url;link.download=img.relative_path.replace(/\.[^.]+$/,'')+'.features.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    };
    drawFeature();
  }
}
function labelFor(key,index){
  if(key==='geometry')return ['Aspect Ratio','Solidity','Extent'][index];
  if(key==='color_moments')return ['μR','μG','μB','σR','σG','σB','τR','τG','τB'][index];
  if(key==='fourier')return 'D'+(index+2);
  if(key==='glcm')return `(${feature.parameters.glcm_offsets[Math.floor(index/5)].join(',')}) · ${['ASM','Contrast','Homogeneity','Correlation','Entropy'][index%5]}`;
  if(key==='spatial_hsv'){const bins=feature.hsv.length;return `R${Math.floor(index/bins)+1} · bin ${index%bins}`;}
  return (key==='contour_profile'?'Điểm ':'Bin ')+index;
}
function drawFeature(){
  const key=$('feature-choice').value, values=feature[key];
  $('feature-description').textContent=groups[key][1];
  const low=Math.min(0,...values),high=Math.max(0.000001,...values),range=high-low;
  const W=900,H=200,left=64,right=15,top=12,bottom=29;
  const y=v=>top+(high-v)/range*(H-top-bottom),zero=y(0),width=(W-left-right)/values.length;
  let svg=`<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Biểu đồ ${esc(groups[key][0])}">`;
  for(let i=0;i<4;i++){
    const value=low+range*i/3,cy=y(value);
    svg+=`<line x1="${left}" x2="${W-right}" y1="${cy}" y2="${cy}" stroke="#e4ece6"/><text x="${left-8}" y="${cy+4}" text-anchor="end" class="chart-text">${Number(value.toPrecision(3))}</text>`;
  }
  if(key==='contour_profile'){
    svg+=`<polyline fill="none" stroke="#227a58" stroke-width="2" points="${values.map((v,i)=>`${left+i*width},${y(v)}`).join(' ')}"/>`;
  }else{
    svg+=values.map((v,i)=>`<rect x="${left+i*width}" y="${Math.min(y(v),zero)}" width="${Math.max(.3,width*.85)}" height="${Math.max(.3,Math.abs(y(v)-zero))}" fill="${v<0?'#b66e43':'#2b8a65'}"><title>${esc(labelFor(key,i))}: ${v}</title></rect>`).join('');
  }
  svg+=`<text x="${left}" y="${H-6}" class="chart-text">0</text><text x="${W-right}" y="${H-6}" text-anchor="end" class="chart-text">${values.length-1} · chỉ số thành phần</text></svg>`;
  $('chart').innerHTML=svg;
  $('vector-table').innerHTML=values.map((v,i)=>`<tr><td>${esc(labelFor(key,i))}</td><td>${esc(v)}</td></tr>`).join('');
}
$('filters').onsubmit=e=>{e.preventDefault();page=1;notice('');loadGallery();};
$('species').onchange=()=>{page=1;loadGallery();};
$('previous').onclick=()=>{page--;loadGallery();};
$('next').onclick=()=>{page++;loadGallery();};
$('refresh').onclick=refresh;
$('close-detail').onclick=()=>{$('detail').close();detailRequest++;};
$('detail').addEventListener('click',e=>{if(e.target===$('detail')){const r=$('detail').getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)$('detail').close();}});
refresh();
