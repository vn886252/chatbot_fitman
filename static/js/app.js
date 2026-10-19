/* ===================================================================
   FITMAN SPORTSWEAR — FRONTEND APPLICATION LOGIC (PHASE 1)
   =================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  initCatalog();
  initPricingCalculator();
  initSizeFinder();
  initFaqAccordion();
  initCartDrawer();
  initLightbox();
});

/* ===================================================================
   1. PRODUCT CATALOG DATA & RENDERING
   =================================================================== */
const PRODUCTS = [
  {
    id: "M1",
    name: "Áo Thun Gym Oversize Fitman Mẫu Mới 1",
    category: "new",
    categoryName: "Mẫu mới 2026",
    price: 150000,
    fabric: "100% Cotton 260GSM",
    image: "/static/products/mau_moi_1.png",
    badge: "MẪU MỚI 2026",
    badgeColor: "orange",
    desc: "Tone Trắng / Kem cát sang trọng, form CBUM vai rộng bắp tay ôm, thoáng mát giữ form cực lâu."
  },
  {
    id: "M2",
    name: "Áo Thun Gym Oversize Fitman Mẫu Mới 2",
    category: "new",
    categoryName: "Mẫu mới 2026",
    price: 150000,
    fabric: "100% Cotton 260GSM",
    image: "/static/products/mau_moi_2.png",
    badge: "MẪU MỚI 2026",
    badgeColor: "orange",
    desc: "Tone Đen huyền bí, họa tiết graphic thể thao sắc nét, che khuyết điểm tôn cơ bắp ngực xô."
  },
  {
    id: "NHOM_1",
    name: "Bộ Sưu Tập Áo CBUM Olympia Dòng 1",
    category: "ao",
    categoryName: "Áo Oversize Gym",
    price: 150000,
    fabric: "100% Cotton 260GSM",
    image: "/static/products/nhom_1.jpg",
    badge: "BEST SELLER",
    badgeColor: "dark",
    desc: "Gồm các mã hot: 1, 4, 5, 6, 15, 16, 17, 19, 20. Bản in chất lượng cao không bong tróc."
  },
  {
    id: "NHOM_2",
    name: "Bộ Sưu Tập Áo CBUM Standard Dòng 2",
    category: "ao",
    categoryName: "Áo Oversize Gym",
    price: 150000,
    fabric: "100% Cotton 260GSM",
    image: "/static/products/nhom_2.jpg",
    badge: "POPULAR",
    badgeColor: "dark",
    desc: "Gồm các mã: 2, 3, 7, 8, 9, 10, 11, 12, 14. Thiết kế đa dạng dễ phối đồ đi tập hoặc đi chơi."
  },
  {
    id: "NHOM_4",
    name: "Bộ Sưu Tập Áo Wolves & Skull Punisher",
    category: "ao",
    categoryName: "Áo Oversize Gym",
    price: 150000,
    fabric: "100% Cotton 260GSM",
    image: "/static/products/nhom_4.jpg",
    badge: "WOLVES STYLE",
    badgeColor: "orange",
    desc: "Gồm các mã W1, W2, W7, 28, 29 và các tone Nâu, Trắng, Đen, Be. Phong cách punk thể thao mạnh mẽ."
  },
  {
    id: "NHOM_5",
    name: "Bộ Sưu Tập Champion 43 & Big Boi",
    category: "ao",
    categoryName: "Áo Oversize Gym",
    price: 150000,
    fabric: "100% Cotton 260GSM",
    image: "/static/products/nhom_5.jpg",
    badge: "HOT COMBO",
    badgeColor: "dark",
    desc: "Gồm mã áo 30, 31, 32, 34, 35, 36, 39 kết hợp cùng quần short thể thao Q6, Q7 đồng bộ."
  },
  {
    id: "NHOM_6",
    name: "Bộ Sưu Tập Áo Never Quitting Olympia",
    category: "ao",
    categoryName: "Áo Oversize Gym",
    price: 150000,
    fabric: "100% Cotton 260GSM",
    image: "/static/products/nhom_6.jpg",
    badge: "CBUM 5X",
    badgeColor: "dark",
    desc: "Gồm các mã 43, 44, 45, 46, 47 truyền cảm hứng tập luyện bền bỉ, tôn form vai xô tuyệt đỉnh."
  },
  {
    id: "NHOM_3",
    name: "Quần Đùi Tập Gym CBUM Pro Short",
    category: "quan",
    categoryName: "Quần Đùi Gym",
    price: 150000,
    fabric: "Dù co giãn 4 chiều",
    image: "/static/products/nhom_3.jpg",
    badge: "PRO SHORT",
    badgeColor: "orange",
    desc: "Mã Q1, Q2, Q3, Q4: Thiết kế xẻ tà đùi tối ưu squat và leg day, thoáng khí, có túi khóa kéo tiện lợi."
  }
];

function initCatalog() {
  const grid = document.getElementById('productGrid');
  const tabBtns = document.querySelectorAll('.tab-btn');
  if (!grid) return;

  function render(category = 'all') {
    const filtered = category === 'all' 
      ? PRODUCTS 
      : PRODUCTS.filter(p => p.category === category);

    grid.innerHTML = filtered.map(p => `
      <article class="product-card" data-id="${p.id}" data-category="${p.category}">
        <div class="product-media" onclick="openLightbox('${p.image}', '${p.name}')">
          <img src="${p.image}" alt="${p.name} - Fitman Sportswear" loading="lazy" />
          <div class="product-badges">
            <span class="badge badge-${p.badgeColor}">${p.badge}</span>
          </div>
        </div>
        <div class="product-body">
          <span class="product-category">${p.categoryName}</span>
          <h3 class="product-name">${p.name}</h3>
          <p class="product-meta"><strong>Vải:</strong> ${p.fabric}</p>
          <div class="product-pricing">
            <span class="price-current">${formatMoney(p.price)}</span>
            <span class="price-unit">/ áo hoặc quần</span>
          </div>
          <div class="product-actions">
            <button class="btn btn-primary btn-add-cart" onclick="addToCart('${p.id}')">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"></path><line x1="3" y1="6" x2="21" y2="6"></line><path d="M16 10a4 4 0 0 1-8 0"></path></svg>
              Chọn Mua
            </button>
            <button class="btn-zoom" title="Xem ảnh to" onclick="openLightbox('${p.image}', '${p.name}')">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line><line x1="11" y1="8" x2="11" y2="14"></line><line x1="8" y1="11" x2="14" y2="11"></line></svg>
            </button>
          </div>
        </div>
      </article>
    `).join('');
  }

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      render(btn.dataset.category);
    });
  });

  render('all');
}

/* ===================================================================
   2. INTERACTIVE PRICING COMBO CALCULATOR
   =================================================================== */
function initPricingCalculator() {
  const options = document.querySelectorAll('.calc-option');
  const resultPrice = document.getElementById('calcResultPrice');
  const resultDesc = document.getElementById('calcResultDesc');
  const resultBenefit = document.getElementById('calcResultBenefit');

  if (!options.length) return;

  const PRICING_RULES = {
    1: { price: 180000, desc: "1 áo 150.000đ + 30.000đ tiền ship COD toàn quốc", benefit: "Tip: Thêm 1 áo chỉ bù 119k là được FREESHIP ngay!" },
    2: { price: 299000, desc: "2 áo giá 299.000đ — MIỄN PHÍ VẬN CHUYỂN TOÀN QUỐC", benefit: "🔥 Tiết kiệm 61.000đ so với mua lẻ từng áo!" },
    3: { price: 399000, desc: "3 áo giá 399.000đ — FREESHIP (Tính ra chỉ 133k/áo)", benefit: "🔥 Siêu hời! Thêm 1 áo nữa chỉ đúng 100k!" },
    4: { price: 520000, desc: "4 áo giá 520.000đ — FREESHIP (Đồng giá 130k/áo từ cái thứ 4)", benefit: "🔥 Giá sỉ ưu đãi: Chỉ 130.000đ/áo + Miễn phí vận chuyển!" },
    5: { price: 650000, desc: "5 áo giá 650.000đ — FREESHIP (Đồng giá 130k/áo)", benefit: "🔥 Mặc cả tuần không lo trùng mẫu, tiết kiệm tối đa!" }
  };

  options.forEach(opt => {
    opt.addEventListener('click', () => {
      options.forEach(o => o.classList.remove('active'));
      opt.classList.add('active');
      const count = parseInt(opt.dataset.count, 10);
      const rule = PRICING_RULES[count] || PRICING_RULES[1];
      
      if (resultPrice) resultPrice.textContent = formatMoney(rule.price);
      if (resultDesc) resultDesc.textContent = rule.desc;
      if (resultBenefit) resultBenefit.textContent = rule.benefit;
    });
  });
}

/* ===================================================================
   3. SMART SIZE FINDER
   =================================================================== */
function initSizeFinder() {
  const heightSlider = document.getElementById('heightSlider');
  const weightSlider = document.getElementById('weightSlider');
  const heightVal = document.getElementById('heightVal');
  const weightVal = document.getElementById('weightVal');
  const sizeOutput = document.getElementById('sizeOutput');
  const sizeAdvice = document.getElementById('sizeAdvice');

  if (!heightSlider || !weightSlider) return;

  function calculateSize() {
    const h = parseInt(heightSlider.value, 10);
    const w = parseInt(weightSlider.value, 10);

    if (heightVal) heightVal.textContent = `${h} cm`;
    if (weightVal) weightVal.textContent = `${w} kg`;

    let recommendedSize = 'M';
    let adviceText = '';

    if (w < 62) {
      recommendedSize = 'S';
      adviceText = `Với cân nặng ${w}kg, bạn mặc Size S chuẩn form Oversize thoải mái, vừa vặn vai xô.`;
    } else if (w <= 72) {
      recommendedSize = 'M';
      adviceText = `Với chiều cao ${h}cm và ${w}kg, Size M là kích thước chuẩn nhất tôn cơ bắp ngực và xô.`;
    } else if (w <= 83) {
      recommendedSize = 'L';
      adviceText = `Thể hình vạm vỡ (${w}kg) nên mặc Size L chuẩn form CBUM phủ mông, tay áo che bắp tay đẹp mắt.`;
    } else if (w <= 95) {
      recommendedSize = 'XL';
      adviceText = `Cân nặng ${w}kg mặc Size XL cực kỳ phong cách, rộng rãi đúng chuẩn streetwear thể thao.`;
    } else {
      recommendedSize = '2XL';
      adviceText = `Trên 95kg, Fitman có hỗ trợ tư vấn đặt may hoặc Size 2XL siêu rộng rãi.`;
    }

    if (sizeOutput) sizeOutput.textContent = recommendedSize;
    if (sizeAdvice) sizeAdvice.textContent = adviceText;
  }

  heightSlider.addEventListener('input', calculateSize);
  weightSlider.addEventListener('input', calculateSize);
  calculateSize();
}

/* ===================================================================
   4. FAQ ACCORDION (AEO FRIENDLY)
   =================================================================== */
function initFaqAccordion() {
  const faqItems = document.querySelectorAll('.faq-item');
  faqItems.forEach(item => {
    const btn = item.querySelector('.faq-question');
    if (!btn) return;
    btn.addEventListener('click', () => {
      const isActive = item.classList.contains('active');
      faqItems.forEach(i => i.classList.remove('active'));
      if (!isActive) item.classList.add('active');
    });
  });
}

/* ===================================================================
   5. LIGHTBOX MODAL
   =================================================================== */
function initLightbox() {
  const modal = document.getElementById('lightboxModal');
  const closeBtn = document.getElementById('lightboxClose');
  if (!modal || !closeBtn) return;

  closeBtn.addEventListener('click', closeLightbox);
  modal.addEventListener('click', (e) => {
    if (e.target === modal) closeLightbox();
  });
}

function openLightbox(src, alt) {
  const modal = document.getElementById('lightboxModal');
  const img = document.getElementById('lightboxImg');
  if (modal && img) {
    img.src = src;
    img.alt = alt || 'Ảnh sản phẩm Fitman';
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }
}

function closeLightbox() {
  const modal = document.getElementById('lightboxModal');
  if (modal) {
    modal.classList.remove('active');
    document.body.style.overflow = '';
  }
}

/* ===================================================================
   6. SIMPLE CART DRAWER
   =================================================================== */
let cartItems = [];

function initCartDrawer() {
  const openBtn = document.getElementById('cartOpenBtn');
  const closeBtn = document.getElementById('cartCloseBtn');
  const overlay = document.getElementById('cartOverlay');
  const drawer = document.getElementById('cartDrawer');

  if (openBtn) openBtn.addEventListener('click', openCart);
  if (closeBtn) closeBtn.addEventListener('click', closeCart);
  if (overlay) overlay.addEventListener('click', closeCart);
}

function openCart() {
  document.getElementById('cartOverlay')?.classList.add('active');
  document.getElementById('cartDrawer')?.classList.add('active');
  document.body.style.overflow = 'hidden';
  renderCart();
}

function closeCart() {
  document.getElementById('cartOverlay')?.classList.remove('active');
  document.getElementById('cartDrawer')?.classList.remove('active');
  document.body.style.overflow = '';
}

function addToCart(productId) {
  const prod = PRODUCTS.find(p => p.id === productId);
  if (!prod) return;

  const existing = cartItems.find(item => item.id === productId);
  if (existing) {
    existing.qty += 1;
  } else {
    cartItems.push({ ...prod, qty: 1 });
  }

  updateCartBadge();
  openCart();
}

function updateCartQty(productId, delta) {
  const item = cartItems.find(i => i.id === productId);
  if (!item) return;

  item.qty += delta;
  if (item.qty <= 0) {
    cartItems = cartItems.filter(i => i.id !== productId);
  }
  updateCartBadge();
  renderCart();
}

function updateCartBadge() {
  const badge = document.getElementById('cartBadge');
  const totalQty = cartItems.reduce((sum, item) => sum + item.qty, 0);
  if (badge) badge.textContent = totalQty;
}

function renderCart() {
  const body = document.getElementById('cartBody');
  const totalElem = document.getElementById('cartTotal');
  const discountElem = document.getElementById('cartDiscountInfo');
  if (!body) return;

  const totalQty = cartItems.reduce((sum, item) => sum + item.qty, 0);

  if (cartItems.length === 0) {
    body.innerHTML = `
      <div class="cart-empty">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#D4D4D8" stroke-width="1.5"><circle cx="9" cy="21" r="1"></circle><circle cx="20" cy="21" r="1"></circle><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path></svg>
        <p style="margin-top: 12px; font-weight: 500;">Giỏ hàng của bạn đang trống</p>
        <a href="#catalog" onclick="closeCart()" class="btn btn-outline" style="margin-top: 16px; font-size: 0.85rem;">Khám phá mẫu ngay</a>
      </div>
    `;
    if (totalElem) totalElem.textContent = "0đ";
    if (discountElem) discountElem.textContent = "Thêm 2 áo để được FREESHIP";
    return;
  }

  // Calculate pricing based on combo rules
  let calculatedTotal = 0;
  let discountNote = "";

  if (totalQty === 1) {
    calculatedTotal = 150000 + 30000;
    discountNote = "Phí ship 30k. Thêm 1 món nữa để được FREESHIP!";
  } else if (totalQty === 2) {
    calculatedTotal = 299000;
    discountNote = "🎉 Bạn được FREESHIP toàn quốc! Thêm 1 món chỉ thêm 100k!";
  } else if (totalQty === 3) {
    calculatedTotal = 399000;
    discountNote = "🎉 Bạn được FREESHIP toàn quốc! Combo 3 món siêu tiết kiệm!";
  } else if (totalQty >= 4) {
    calculatedTotal = totalQty * 130000;
    discountNote = `🎉 Đồng giá sỉ ${formatMoney(130000)}/món + FREESHIP toàn quốc!`;
  }

  body.innerHTML = cartItems.map(item => `
    <div style="display: flex; gap: 12px; padding-bottom: 12px; border-bottom: 1px solid #F4F4F5; align-items: center;">
      <img src="${item.image}" alt="${item.name}" style="width: 60px; height: 60px; object-fit: cover; border-radius: 8px;" />
      <div style="flex-grow: 1;">
        <h4 style="font-size: 0.9rem; font-weight: 700; color: #18181B; margin-bottom: 2px;">${item.name}</h4>
        <span style="font-size: 0.82rem; color: #FF7A1A; font-weight: 700;">150.000đ</span>
      </div>
      <div style="display: flex; align-items: center; gap: 6px;">
        <button onclick="updateCartQty('${item.id}', -1)" style="width: 26px; height: 26px; background: #F4F4F5; border-radius: 4px; font-weight: bold;">-</button>
        <span style="font-weight: 600; font-size: 0.9rem; min-width: 18px; text-align: center;">${item.qty}</span>
        <button onclick="updateCartQty('${item.id}', 1)" style="width: 26px; height: 26px; background: #F4F4F5; border-radius: 4px; font-weight: bold;">+</button>
      </div>
    </div>
  `).join('');

  if (totalElem) totalElem.textContent = formatMoney(calculatedTotal);
  if (discountElem) discountElem.textContent = discountNote;
}

function formatMoney(amount) {
  return amount.toLocaleString('vi-VN') + 'đ';
}

function proceedToCheckout() {
  if (cartItems.length === 0) return;
  const summary = cartItems.map(i => `${i.qty}x ${i.name}`).join(', ');
  const fbUrl = `https://m.me/fitmansportswear?text=${encodeURIComponent('Chào Fitman, mình muốn đặt các món sau: ' + summary)}`;
  window.open(fbUrl, '_blank');
}

/* ===================================================================
   7. CUSTOM DESIGN STUDIO LOGIC
   =================================================================== */
let studioState = {
  color: '#FFFFFF',
  colorName: 'Trắng Tinh',
  colorBorder: '#D4D4D8',
  size: 'M',
  side: 'front', // 'front' | 'back'
  artUrl: '/static/brand/logo_icon.png',
  artName: 'Tạ Cam Fitman',
  placementClass: 'placement-center-chest',
  placementName: 'Giữa Ngực',
  price: 190000,
  orderCode: 'FITMAN' + Math.floor(1000 + Math.random() * 9000)
};

function selectShirtColor(hex, name, border, elem) {
  studioState.color = hex;
  studioState.colorName = name;
  studioState.colorBorder = border;

  // Cập nhật SVG path
  const baseShape = document.getElementById('shirtBaseShape');
  const collar = document.getElementById('shirtCollar');
  if (baseShape) {
    baseShape.setAttribute('fill', hex);
    baseShape.setAttribute('stroke', border);
  }
  if (collar) {
    if (hex === '#18181B' || hex === '#534B3C' || hex === '#3B443B' || hex === '#71717A') {
      collar.setAttribute('fill', hex);
      collar.setAttribute('stroke', border);
    } else {
      collar.setAttribute('fill', '#E4E4E7');
      collar.setAttribute('stroke', '#A1A1AA');
    }
  }

  // Active class
  document.querySelectorAll('.swatch-item').forEach(el => el.classList.remove('active'));
  if (elem) elem.classList.add('active');
}

function switchShirtSide(side) {
  studioState.side = side;
  const frontBtn = document.getElementById('flipFrontBtn');
  const backBtn = document.getElementById('flipBackBtn');
  const collar = document.getElementById('shirtCollar');

  if (side === 'front') {
    frontBtn?.classList.add('active');
    backBtn?.classList.remove('active');
    if (collar) collar.style.display = 'block';
  } else {
    backBtn?.classList.add('active');
    frontBtn?.classList.remove('active');
    if (collar) collar.style.display = 'none'; // Mặt sau áo
  }

  updateStageViewingText();
}

function selectStudioSize(size, elem) {
  studioState.size = size;
  document.querySelectorAll('.size-btn').forEach(el => el.classList.remove('active'));
  if (elem) elem.classList.add('active');
}

function switchArtTab(tab) {
  const libBtn = document.getElementById('tabLibraryBtn');
  const upBtn = document.getElementById('tabUploadBtn');
  const libBox = document.getElementById('artLibraryBox');
  const upBox = document.getElementById('artUploadBox');

  if (tab === 'library') {
    libBtn?.classList.add('active');
    upBtn?.classList.remove('active');
    if (libBox) libBox.style.display = 'grid';
    if (upBox) upBox.style.display = 'none';
  } else {
    upBtn?.classList.add('active');
    libBtn?.classList.remove('active');
    if (libBox) libBox.style.display = 'none';
    if (upBox) upBox.style.display = 'block';
  }
}

function selectStudioArtwork(url, name, elem) {
  studioState.artUrl = url;
  studioState.artName = name;
  const overlayImg = document.getElementById('overlayArtworkImg');
  if (overlayImg) {
    overlayImg.src = url;
    overlayImg.alt = name;
  }
  document.querySelectorAll('.art-card').forEach(el => el.classList.remove('active'));
  if (elem) elem.classList.add('active');
}

function handleCustomFileUpload(event) {
  const file = event.target.files?.[0];
  if (!file) return;

  if (file.size > 10 * 1024 * 1024) {
    alert("Vui lòng tải file ảnh dưới 10MB!");
    return;
  }

  const reader = new FileReader();
  reader.onload = function(e) {
    const dataUrl = e.target.result;
    studioState.artUrl = dataUrl;
    studioState.artName = `Custom: ${file.name}`;
    const overlayImg = document.getElementById('overlayArtworkImg');
    if (overlayImg) {
      overlayImg.src = dataUrl;
      overlayImg.alt = file.name;
    }
  };
  reader.readAsDataURL(file);
}

function selectPlacement(placementClass, side, name, elem) {
  studioState.placementClass = placementClass;
  studioState.placementName = name;

  if (side !== studioState.side) {
    switchShirtSide(side);
  }

  const overlay = document.getElementById('printOverlay');
  if (overlay) {
    overlay.className = 'print-overlay-zone ' + placementClass;
  }

  document.querySelectorAll('.place-btn').forEach(el => el.classList.remove('active'));
  if (elem) elem.classList.add('active');

  updateStageViewingText();
}

function updateStageViewingText() {
  const textElem = document.getElementById('stageViewingText');
  if (textElem) {
    const sideStr = studioState.side === 'front' ? 'Mặt Trước' : 'Mặt Sau';
    textElem.textContent = `${sideStr} • ${studioState.placementName}`;
  }
}

async function openVietQRModal() {
  studioState.orderCode = 'FITMAN' + Math.floor(1000 + Math.random() * 9000);
  const modal = document.getElementById('vietqrModal');
  const qrImg = document.getElementById('vietqrImage');
  const bankAccNo = document.getElementById('bankAccNo');
  const bankAmount = document.getElementById('bankAmount');
  const bankMemo = document.getElementById('bankMemo');

  try {
    const res = await fetch(`/api/payment/vietqr?amount=${studioState.price}&memo=${encodeURIComponent(studioState.orderCode)}`);
    if (res.ok) {
      const data = await res.json();
      if (qrImg) qrImg.src = data.qr_image_url;
      if (bankAccNo) bankAccNo.textContent = data.account_no;
      if (bankAmount) bankAmount.textContent = formatMoney(data.amount);
      if (bankMemo) bankMemo.textContent = data.memo;
    }
  } catch (err) {
    console.error("Lỗi lấy thông tin VietQR:", err);
  }

  if (modal) {
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }
}

function closeVietQRModal() {
  const modal = document.getElementById('vietqrModal');
  if (modal) {
    modal.classList.remove('active');
    document.body.style.overflow = '';
  }
}

async function submitCustomOrder(event) {
  event.preventDefault();
  const name = document.getElementById('custNameInput')?.value.trim();
  const phone = document.getElementById('custPhoneInput')?.value.trim();
  const address = document.getElementById('custAddressInput')?.value.trim();
  const note = document.getElementById('custNoteInput')?.value.trim();
  const statusMsg = document.getElementById('orderStatusMessage');
  const submitBtn = document.getElementById('submitOrderBtn');

  if (!name || !phone || !address) {
    alert("Vui lòng điền đầy đủ họ tên, số điện thoại và địa chỉ nhận hàng!");
    return;
  }

  const payload = {
    ten_khach_hang: name,
    so_dien_thoai: phone,
    dia_chi: address,
    mau_ao: studioState.colorName,
    size_ao: studioState.size,
    vi_tri_in: `${studioState.side === 'front' ? 'Mặt Trước' : 'Mặt Sau'} - ${studioState.placementName}`,
    ten_mau_in: studioState.artName,
    anh_in_url: studioState.artUrl.startsWith('data:') ? '(Ảnh khách tải lên)' : studioState.artUrl,
    tong_tien: studioState.price,
    ghi_chu: `[Mã CK: ${studioState.orderCode}] ${note}`
  };

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = 'Đang xử lý đơn hàng...';
  }

  try {
    const res = await fetch('/api/custom-order', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const result = await res.json();

    if (statusMsg) {
      statusMsg.style.display = 'block';
      if (result.success) {
        statusMsg.style.background = '#ECFDF5';
        statusMsg.style.color = '#065F46';
        statusMsg.style.border = '1px solid #A7F3D0';
        statusMsg.innerHTML = `
          <strong>🎉 Đã nhận đơn hàng thành công! (Mã #${result.order_number || result.order_id})</strong><br/>
          Cảm ơn bạn! Xưởng in Fitman sẽ kiểm tra chuyển khoản và liên hệ qua số <strong>${phone}</strong> để xác nhận và in áo ngay!
        `;
        if (submitBtn) {
          submitBtn.textContent = '✅ Đơn Hàng Đã Gửi Thành Công';
          submitBtn.style.background = '#10B981';
        }
      } else {
        statusMsg.style.background = '#FEF2F2';
        statusMsg.style.color = '#991B1B';
        statusMsg.style.border = '1px solid #FECACA';
        statusMsg.textContent = 'Có lỗi xảy ra: ' + (result.error || 'Vui lòng thử lại sau.');
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = '✅ Tôi Đã Chuyển Khoản & Xác Nhận Đơn Hàng';
        }
      }
    }
  } catch (err) {
    console.error(err);
    if (statusMsg) {
      statusMsg.style.display = 'block';
      statusMsg.style.background = '#FEF2F2';
      statusMsg.style.color = '#991B1B';
      statusMsg.textContent = 'Lỗi kết nối máy chủ. Vui lòng thử lại hoặc liên hệ hotline.';
    }
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = '✅ Tôi Đã Chuyển Khoản & Xác Nhận Đơn Hàng';
    }
  }
}

