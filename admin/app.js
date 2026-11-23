let products = [];

const $ = (selector) => document.querySelector(selector);
const esc = (value = "") => String(value).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));

async function request(url, options = {}) {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || payload.stderr || `HTTP ${response.status}`);
  return payload;
}

function blankProduct(item = {}) {
  return {
    enabled: item.enabled ?? true,
    name: item.name || "",
    source_id: item.source_id || "",
    code: item.code || "",
    barcode: item.barcode || "",
    producer_code: item.producer_code || "",
    images: Array.isArray(item.images) ? item.images : [],
  };
}

function renderProducts() {
  $('#activeCount').textContent = products.filter(p => p.enabled).length;
  $('#products').innerHTML = products.map((p, index) => `
    <article class="product-card" data-index="${index}">
      <div class="product-card-head">
        <label><input type="checkbox" data-field="enabled" ${p.enabled ? 'checked' : ''}> Aktif</label>
        <button class="danger" data-remove="${index}">Kaldır</button>
      </div>
      <div class="fields">
        <label>Ürün adı<input data-field="name" value="${esc(p.name)}"></label>
        <label>Ürün kodu<input data-field="code" value="${esc(p.code)}"></label>
        <label>Barkod<input data-field="barcode" value="${esc(p.barcode)}"></label>
        <label>Üretici kodu<input data-field="producer_code" value="${esc(p.producer_code)}"></label>
        <label>Kaynak ID<input data-field="source_id" value="${esc(p.source_id)}"></label>
      </div>
      <label class="images-label">Ek görseller — her satıra bir URL
        <textarea data-field="images">${esc((p.images || []).join('\n'))}</textarea>
      </label>
    </article>
  `).join('');
}

function syncFromForm() {
  document.querySelectorAll('.product-card').forEach(card => {
    const index = Number(card.dataset.index);
    card.querySelectorAll('[data-field]').forEach(input => {
      const field = input.dataset.field;
      if (field === 'enabled') products[index][field] = input.checked;
      else if (field === 'images') products[index][field] = input.value.split('\n').map(x => x.trim()).filter(Boolean);
      else products[index][field] = input.value.trim();
    });
  });
}

async function load() {
  const state = await request('/api/state');
  products = state.products.map(blankProduct);
  renderProducts();
  if (state.status) {
    $('#lastBuild').textContent = new Date(state.status.generated_at_utc).toLocaleString('tr-TR');
    $('#buildStatus').textContent = `${state.status.selected_product_count} ürün hazır`;
  }
}

async function save() {
  syncFromForm();
  const invalid = products.find(p => p.enabled && !p.code && !p.barcode && !p.producer_code && !p.source_id);
  if (invalid) throw new Error('Aktif ürünlerden birinin hiçbir eşleştirme alanı dolu değil.');
  const result = await request('/api/products', {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({products})
  });
  $('#output').textContent = `${result.count} ürün kaydedildi.`;
  renderProducts();
}

$('#products').addEventListener('click', event => {
  const index = event.target.dataset.remove;
  if (index === undefined) return;
  syncFromForm();
  products.splice(Number(index), 1);
  renderProducts();
});

$('#addBlank').addEventListener('click', () => { syncFromForm(); products.push(blankProduct()); renderProducts(); });
$('#save').addEventListener('click', () => save().catch(e => $('#output').textContent = `HATA: ${e.message}`));
$('#build').addEventListener('click', async () => {
  try {
    await save();
    $('#output').textContent = 'Kaynak XML indiriliyor ve filtreleniyor...';
    const result = await request('/api/build', {method: 'POST'});
    $('#output').textContent = result.stdout || result.stderr;
    await load();
  } catch (e) { $('#output').textContent = `HATA: ${e.message}`; }
});

$('#search').addEventListener('click', async () => {
  const q = $('#searchInput').value.trim();
  if (!q) return;
  $('#searchMessage').textContent = 'Kadıoğlu XML indiriliyor...';
  $('#searchResults').innerHTML = '';
  try {
    const result = await request(`/api/source-products?q=${encodeURIComponent(q)}`);
    $('#searchMessage').textContent = `${result.count} sonuç bulundu${result.count > 250 ? ', ilk 250 gösteriliyor' : ''}.`;
    $('#searchResults').innerHTML = result.items.map((item, index) => `
      <div class="result">
        <div><strong>${esc(item.name || 'İsimsiz ürün')}</strong>
          <small>Kod: ${esc(item.code)} · Barkod: ${esc(item.barcode)} · Üretici: ${esc(item.producer_code)} · Stok: ${esc(item.stock)}</small>
        </div>
        <button data-add-result="${index}">Listeye ekle</button>
      </div>
    `).join('');
    window.searchItems = result.items;
  } catch (e) { $('#searchMessage').textContent = `HATA: ${e.message}`; }
});

$('#searchResults').addEventListener('click', event => {
  const index = event.target.dataset.addResult;
  if (index === undefined) return;
  syncFromForm();
  products.push(blankProduct(window.searchItems[Number(index)]));
  renderProducts();
  document.querySelector('.product-list').lastElementChild.scrollIntoView({behavior: 'smooth'});
});

$('#searchInput').addEventListener('keydown', e => { if (e.key === 'Enter') $('#search').click(); });
load().catch(e => $('#output').textContent = `HATA: ${e.message}`);
