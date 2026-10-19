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
    "id": "R1",
    "name": "Áo Thun Gym Oversize Fitman RAW From The Ground Up Đen",
    "category": "raw",
    "categoryName": "RAW",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Đen",
    "image": "/static/products/items/ao-gym-mau-moi-r1-from-the-ground-up-den.jpg",
    "badge": "RAW",
    "badgeColor": "orange",
    "desc": "Tone Đen huyền bí, lưng in đồ họa tròn From The Ground Up RAW cam trắng nổi bật, form CBUM vai rộng che khuyết điểm."
  },
  {
    "id": "R2",
    "name": "Áo Thun Gym Oversize Fitman RAW 3D Mint Trắng Ngà",
    "category": "raw",
    "categoryName": "RAW",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Trắng Ngà",
    "image": "/static/products/items/ao-gym-mau-moi-r2-raw-3d-mint-trang.jpg",
    "badge": "RAW",
    "badgeColor": "orange",
    "desc": "Tone Trắng ngà sang trọng, họa tiết chữ R 3D xanh mint dập nổi trước và sau, cực kỳ tôn cơ bắp khi pump."
  },
  {
    "id": "R3",
    "name": "Áo Thun Gym Oversize Fitman RAW Nutrition R2 Đen",
    "category": "raw",
    "categoryName": "RAW",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Đen",
    "image": "/static/products/items/ao-gym-mau-moi-r3-raw-nutrition-r2-den.jpg",
    "badge": "RAW",
    "badgeColor": "orange",
    "desc": "Tone Đen cá tính, ngực in vòm RAW Nutrition, lưng in khối số R2 phong cách thể hình hiện đại."
  },
  {
    "id": "R4",
    "name": "Áo Thun Gym Oversize Fitman RAW FTGU Kem Cát (Beige)",
    "category": "raw",
    "categoryName": "RAW",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Kem Cát",
    "image": "/static/products/items/ao-gym-mau-moi-r4-ftgu-kem-cat.jpg",
    "badge": "RAW",
    "badgeColor": "orange",
    "desc": "Tone Kem cát thời thượng, lưng in khối R FTGU From The Ground Up viền vàng cam sắc nét chuẩn gu aesthetic."
  },
  {
    "id": "R5",
    "name": "Áo Thun Gym Oversize Fitman Borderline Obsessed RAW Đen",
    "category": "raw",
    "categoryName": "RAW",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Đen",
    "image": "/static/products/items/ao-gym-mau-moi-r5-borderline-obsessed-den.jpg",
    "badge": "RAW",
    "badgeColor": "orange",
    "desc": "Studio mockup độc quyền Fitman, lưng in hiệu ứng bụi phấn thể hình Borderline Obsessed cam rực lửa."
  },
  {
    "id": "R6",
    "name": "Áo Thun Gym Oversize Fitman RAW University Rec League Trắng",
    "category": "raw",
    "categoryName": "RAW",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Trắng",
    "image": "/static/products/items/ao-gym-mau-moi-r6-raw-university-trang.jpg",
    "badge": "RAW",
    "badgeColor": "orange",
    "desc": "Tone Trắng ngực in vòm RAW MMXX, lưng in đại tự R University Rec League phong cách đại học thể thao Mỹ."
  },
  {
    "id": "R7",
    "name": "Áo Thun Gym Oversize Fitman RAW Nutrition Xanh Rêu",
    "category": "raw",
    "categoryName": "RAW",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Xanh Rêu",
    "image": "/static/products/items/ao-gym-mau-moi-r7-raw-nutrition-xanh-reu.jpg",
    "badge": "RAW",
    "badgeColor": "orange",
    "desc": "Tone Xanh Rêu Forest Green đậm đà nam tính, lưng in logo R Nutrition to bản tôn lưng xô chữ V."
  },
  {
    "id": "R8",
    "name": "Áo Thun Gym Oversize Fitman RAW From The Ground Up Đen Basic",
    "category": "raw",
    "categoryName": "RAW",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Đen",
    "image": "/static/products/items/ao-gym-mau-moi-r8-raw-ftgu-basic-den.jpg",
    "badge": "RAW",
    "badgeColor": "orange",
    "desc": "Tone Đen ngực in logo R, lưng in chữ khối FROM THE GROUND UP bạc xám tinh tế, cực dễ phối đồ tập."
  },
  {
    "id": "YL10",
    "name": "Áo Thun Gym Oversize Fitman YoungLA Spike Bulldog Đen Washed",
    "category": "youngla",
    "categoryName": "YoungLA",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM Washed",
    "color": "Đen Washed",
    "image": "/static/products/items/ao-gym-mau-moi-yl10-youngla-spike-bulldog.jpg",
    "badge": "YOUNGLA",
    "badgeColor": "dark",
    "desc": "Phong cách Vintage Washed bụi bặm, đồ họa chú chó Bulldog Spike YoungLA hung tợn đậm chất phòng gym."
  },
  {
    "id": "YL11",
    "name": "Áo Thun Gym Oversize Fitman YoungLA Tom & Jerry Đen",
    "category": "youngla",
    "categoryName": "YoungLA",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Đen",
    "image": "/static/products/items/ao-gym-mau-moi-yl11-youngla-tom-jerry-den.jpg",
    "badge": "YOUNGLA",
    "badgeColor": "dark",
    "desc": "Mẫu YoungLA x Tom & Jerry tone Đen cá tính, 2 mặt in đồ họa sắc nét, trẻ trung năng động và nổi bật."
  },
  {
    "id": "YL12",
    "name": "Áo Thun Gym Oversize Fitman YoungLA Tom & Jerry Kem Be",
    "category": "youngla",
    "categoryName": "YoungLA",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Kem Be",
    "image": "/static/products/items/ao-gym-mau-moi-yl12-youngla-tom-jerry-kem.jpg",
    "badge": "YOUNGLA",
    "badgeColor": "dark",
    "desc": "Mẫu YoungLA x Tom & Jerry tone Kem Be vintage, vải mềm mịn dày dặn đứng form cực chuẩn khi diện đi chơi hoặc đi gym."
  },
  {
    "id": "B1",
    "name": "Áo Thun Gym Oversize Fitman Basketball Championship Đen",
    "category": "cbum",
    "categoryName": "CBUM",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Đen",
    "image": "/static/products/items/ao-gym-mau-moi-b1-basketball-den.jpg",
    "badge": "CBUM",
    "badgeColor": "dark",
    "desc": "Tone Đen, lưng in 4 ô động tác bóng rổ màu cam nổi bật, tinh thần thi đấu bùng nổ."
  },
  {
    "id": "B2",
    "name": "Áo Thun Gym Oversize Fitman Basketball Championship Trắng",
    "category": "cbum",
    "categoryName": "CBUM",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Trắng",
    "image": "/static/products/items/ao-gym-mau-moi-b2-basketball-trang.jpg",
    "badge": "CBUM",
    "badgeColor": "dark",
    "desc": "Tone Trắng thể thao, lưng in 4 ô động tác thi đấu bóng rổ cam cháy năng động, form rộng thoáng mát."
  },
  {
    "id": "CBUM_01",
    "name": "Áo Thun Gym Oversize Fitman CBUM 3 Bum Lifting Club Đen (Mã 01)",
    "category": "cbum",
    "categoryName": "CBUM",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Đen",
    "image": "/static/products/items/ao-gym-cbum-ma-01-bum-lifting-club-den.jpg",
    "badge": "CBUM",
    "badgeColor": "dark",
    "desc": "Mẫu kinh điển Bum Lifting Club 3 - Set The Damn Standard - Champion Mentality, lưng in to bản tôn trọn xô lưng."
  },
  {
    "id": "CBUM_02",
    "name": "Áo Thun Gym Oversize Fitman CBUM Rắn Hổ Mang Trắng (Mã 02)",
    "category": "cbum",
    "categoryName": "CBUM",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Trắng",
    "image": "/static/products/items/ao-gym-cbum-ma-02-cobra-snake-trang.jpg",
    "badge": "CBUM",
    "badgeColor": "dark",
    "desc": "Tone Trắng tinh tế, lưng in Rắn Hổ Mang Cobra Snake quấn quanh số 3 màu đỏ cam dũng mãnh."
  },
  {
    "id": "CBUM_03",
    "name": "Áo Thun Gym Oversize Fitman CBUM BLC Bum Lifting Club Đen (Mã 03)",
    "category": "cbum",
    "categoryName": "CBUM",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Đen",
    "image": "/static/products/items/ao-gym-cbum-ma-03-blc-den.jpg",
    "badge": "CBUM",
    "badgeColor": "dark",
    "desc": "Ngực in BLC nhỏ gọn, sau lưng in chữ vòm Bum Lifting Club số 3 màu vàng đồng, chuẩn phong cách gym OG."
  },
  {
    "id": "CBUM_04",
    "name": "Áo Thun Gym Oversize Fitman CBUM Mentality 3 Đen (Mã 04)",
    "category": "cbum",
    "categoryName": "CBUM",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Đen",
    "image": "/static/products/items/ao-gym-cbum-ma-04-mentality-den.jpg",
    "badge": "CBUM",
    "badgeColor": "dark",
    "desc": "Lưng in chữ xếp MENTALITY lồng số 3 mạ vàng và 3 vệt móng cào đỏ Set The Standard dũng mãnh."
  },
  {
    "id": "CBUM_06",
    "name": "Áo Thun Gym Oversize Fitman CBUM Claw Vết Cào Đen (Mã 06)",
    "category": "cbum",
    "categoryName": "CBUM",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Đen",
    "image": "/static/products/items/ao-gym-cbum-ma-06-bumstead-claw-den.jpg",
    "badge": "CBUM",
    "badgeColor": "dark",
    "desc": "Trước ngực in BUMSTEAD vàng, sau lưng 4 vệt móng vuốt cào trắng vàng tôn cơ lưng chữ V hoàn hảo."
  },
  {
    "id": "CBUM_07",
    "name": "Áo Thun Gym Oversize Fitman CBUM Rắn Hổ Mang Đen (Mã 07)",
    "category": "cbum",
    "categoryName": "CBUM",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Đen",
    "image": "/static/products/items/ao-gym-cbum-ma-07-cobra-snake-den.jpg",
    "badge": "CBUM",
    "badgeColor": "dark",
    "desc": "Phiên bản tone Đen huyền bí của mẫu Rắn Hổ Mang Cobra quấn số 3 đỏ cam, che khuyết điểm bụng cực tốt."
  },
  {
    "id": "CBUM_08",
    "name": "Áo Thun Gym Oversize Fitman Generate Greatness GG Xanh Rêu (Mã 08)",
    "category": "cbum",
    "categoryName": "CBUM",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Xanh Rêu",
    "image": "/static/products/items/ao-gym-cbum-ma-08-generate-greatness-xanh.jpg",
    "badge": "CBUM",
    "badgeColor": "dark",
    "desc": "Tone Xanh lá / Xanh rêu độc quyền, ngực in chữ ký Generate Greatness, lưng in vòng tròn GG BUM."
  },
  {
    "id": "CBUM_09",
    "name": "Áo Thun Gym Oversize Fitman CBUM Sky Mây Trời Đen (Mã 09)",
    "category": "cbum",
    "categoryName": "CBUM",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Đen",
    "image": "/static/products/items/ao-gym-cbum-ma-09-dream-intent-sky-den.jpg",
    "badge": "CBUM",
    "badgeColor": "dark",
    "desc": "Lưng in số 3 lồng bầu trời mây xanh quang đãng Dream With Intent, phong thái tự do phóng khoáng."
  },
  {
    "id": "CBUM_10",
    "name": "Áo Thun Gym Oversize Fitman CBUM Skull Đầu Lâu Đen (Mã 10)",
    "category": "cbum",
    "categoryName": "CBUM",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Đen",
    "image": "/static/products/items/ao-gym-cbum-ma-10-skull-den.jpg",
    "badge": "CBUM",
    "badgeColor": "dark",
    "desc": "Lưng in đồ họa Đầu Lâu Skull trắng sắc lạnh, phong cách hardcore gym đậm chất chiến binh."
  },
  {
    "id": "CBUM_11",
    "name": "Áo Thun Gym Oversize Fitman CBUM 3UM Shadow Trắng Kem (Mã 11)",
    "category": "cbum",
    "categoryName": "CBUM",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Trắng Kem",
    "image": "/static/products/items/ao-gym-cbum-ma-11-3um-shadow-kem.jpg",
    "badge": "CBUM",
    "badgeColor": "dark",
    "desc": "Tone Trắng kem vintage, ngực in 3UM nhỏ gọn, lưng in 3 tầng bóng đổ 3UM xám đen hiện đại cuốn hút."
  },
  {
    "id": "CBUM_12",
    "name": "Áo Thun Gym Oversize Fitman CBUM Bandana Số 3 Trắng (Mã 12)",
    "category": "cbum",
    "categoryName": "CBUM",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Trắng",
    "image": "/static/products/items/ao-gym-cbum-ma-12-bandana-trang.jpg",
    "badge": "CBUM",
    "badgeColor": "dark",
    "desc": "Tone Trắng, lưng in số 3 họa tiết khăn rằn Bandana Paisley đen, thời trang thể thao đường phố đỉnh cao."
  },
  {
    "id": "CBUM_13",
    "name": "Áo Thun Gym Oversize Fitman CBUM Stay Hungry Hổ Đen (Mã 13)",
    "category": "cbum",
    "categoryName": "CBUM",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Đen",
    "image": "/static/products/items/ao-gym-cbum-ma-13-stay-hungry-tiger-den.jpg",
    "badge": "CBUM",
    "badgeColor": "dark",
    "desc": "Lưng in Mặt Hổ dũng mãnh Stay Hungry Defend The North, biểu tượng cho sự kiên trì và khát khao chiến thắng."
  },
  {
    "id": "CBUM_14",
    "name": "Áo Thun Gym Oversize Fitman CBUM Walk In Like You Own It Đen (Mã 14)",
    "category": "cbum",
    "categoryName": "CBUM",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Đen",
    "image": "/static/products/items/ao-gym-cbum-ma-14-own-it-den.jpg",
    "badge": "CBUM",
    "badgeColor": "dark",
    "desc": "Ngực in OWN IT, sau lưng in chữ cắt đôi WALK IN LIKE YOU OWN IT kèm số 3 dũng khí bản lĩnh."
  },
  {
    "id": "CBUM_15",
    "name": "Áo Thun Gym Oversize Fitman CBUM Bandana Số 3 Đen (Mã 15)",
    "category": "cbum",
    "categoryName": "CBUM",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Đen",
    "image": "/static/products/items/ao-gym-cbum-ma-15-bandana-den.jpg",
    "badge": "CBUM",
    "badgeColor": "dark",
    "desc": "Tone Đen, lưng in số 3 họa tiết khăn Bandana trắng viền nổi, mẫu hot được săn đón nhiều nhất."
  },
  {
    "id": "CBUM_16",
    "name": "Áo Thun Gym Oversize Fitman RAW Nutrition FTGU Nâu (Mã 16)",
    "category": "cbum",
    "categoryName": "CBUM",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Nâu Chocolate",
    "image": "/static/products/items/ao-gym-cbum-ma-16-raw-nutrition-ftgu-nau.jpg",
    "badge": "CBUM",
    "badgeColor": "dark",
    "desc": "Tone Nâu socola cực tây, ngực in RAW trắng, lưng in hình tam giác cách điệu RAW Nutrition FTGU sắc sảo."
  },
  {
    "id": "CBUM_17",
    "name": "Áo Thun Gym Oversize Fitman RAW Members Only Nâu Khaki (Mã 17)",
    "category": "cbum",
    "categoryName": "CBUM",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Nâu Khaki",
    "image": "/static/products/items/ao-gym-cbum-ma-17-members-only-nau.jpg",
    "badge": "CBUM",
    "badgeColor": "dark",
    "desc": "Tone Nâu Khaki cafe cực tây, lưng in RAW Members Only chữ vàng phối đen sang trọng."
  },
  {
    "id": "CBUM_19",
    "name": "Áo Thun Gym Oversize Fitman Pressure & Privilege Olympia Đen (Mã 19)",
    "category": "cbum",
    "categoryName": "CBUM",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Đen",
    "image": "/static/products/items/ao-gym-cbum-ma-19-pressure-privilege-den.jpg",
    "badge": "CBUM",
    "badgeColor": "dark",
    "desc": "Lưng in vòm chữ tròn PRESSURE • PRIVILEGE Olympia MMXXIII Champion Mentality, bản in cao cấp không bong tróc."
  },
  {
    "id": "CBUM_20",
    "name": "Áo Thun Gym Oversize Fitman Generate Greatness GG Đen (Mã 20)",
    "category": "cbum",
    "categoryName": "CBUM",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Đen",
    "image": "/static/products/items/ao-gym-cbum-ma-20-generate-greatness-den.jpg",
    "badge": "CBUM",
    "badgeColor": "dark",
    "desc": "Tone Đen huyền thoại, trước ngực in Generate Greatness uốn lượn kèm logo GG, vải đứng form tôn ngực nở."
  },
  {
    "id": "CBUM_29",
    "name": "Áo Thun Gym Oversize Fitman Big Boi University BBU Trắng Xanh (Mã 29)",
    "category": "cbum",
    "categoryName": "CBUM",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Trắng",
    "image": "/static/products/items/ao-gym-cbum-ma-29-bbu-trang-xanh.jpg",
    "badge": "CBUM",
    "badgeColor": "dark",
    "desc": "Tone Trắng, ngực in chữ BBU lớn và huy hiệu Big Boi University xanh lá đậm phong cách thể thao Mỹ khỏe khoắn."
  },
  {
    "id": "CBUM_30",
    "name": "Áo Thun Gym Oversize Fitman THAVAGE Trắng (Mã 30)",
    "category": "cbum",
    "categoryName": "CBUM",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Trắng",
    "image": "/static/products/items/ao-gym-cbum-ma-30-thavage-trang.jpg",
    "badge": "CBUM",
    "badgeColor": "dark",
    "desc": "Tone Trắng, ngực in chữ THAVAGE đen góc cạnh, tôn trọn vẹn cầu vai và cơ ngực vạm vỡ."
  },
  {
    "id": "CBUM_31",
    "name": "Áo Thun Gym Oversize Fitman THAVAGE Đen (Mã 31)",
    "category": "cbum",
    "categoryName": "CBUM",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Đen",
    "image": "/static/products/items/ao-gym-cbum-ma-31-thavage-den.jpg",
    "badge": "CBUM",
    "badgeColor": "dark",
    "desc": "Tone Đen, ngực in chữ THAVAGE trắng sắc bén, phong cách quái thú phòng gym."
  },
  {
    "id": "CBUM_32",
    "name": "Áo Thun Gym Oversize Fitman THAVAGE Nâu Đậm (Mã 32)",
    "category": "cbum",
    "categoryName": "CBUM",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Nâu Đậm",
    "image": "/static/products/items/ao-gym-cbum-ma-32-thavage-nau.jpg",
    "badge": "CBUM",
    "badgeColor": "dark",
    "desc": "Tone Nâu đất cafe đậm, ngực in chữ THAVAGE trắng nổi bật, dễ phối cùng quần short đen hoặc kem."
  },
  {
    "id": "CBUM_34",
    "name": "Áo Thun Gym Oversize Fitman Champion Mentality 43 Đen (Mã 34)",
    "category": "cbum",
    "categoryName": "CBUM",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Đen",
    "image": "/static/products/items/ao-gym-cbum-ma-34-mentality-43-den.jpg",
    "badge": "CBUM",
    "badgeColor": "dark",
    "desc": "Tone Đen huyền bí, lưng in vòm chữ tròn CHAMPION MENTALITY và số 43 Bum Lifting Club đỏ trắng cực chiến."
  },
  {
    "id": "CBUM_35",
    "name": "Áo Thun Gym Oversize Fitman Champion Mentality 43 Trắng (Mã 35)",
    "category": "cbum",
    "categoryName": "CBUM",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Trắng",
    "image": "/static/products/items/ao-gym-cbum-ma-35-mentality-43-trang.jpg",
    "badge": "CBUM",
    "badgeColor": "dark",
    "desc": "Tone Trắng tinh khôi, lưng in vòm chữ CHAMPION MENTALITY số 43 đen viền đỏ tương phản sang trọng."
  },
  {
    "id": "CBUM_36",
    "name": "Áo Thun Gym Oversize Fitman Champion Mentality 43 Nâu (Mã 36)",
    "category": "cbum",
    "categoryName": "CBUM",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Nâu Chocolate",
    "image": "/static/products/items/ao-gym-cbum-ma-36-mentality-43-nau.jpg",
    "badge": "CBUM",
    "badgeColor": "dark",
    "desc": "Tone Nâu chocolate độc lạ, lưng in CHAMPION MENTALITY 43 phong cách streetwear gym thịnh hành."
  },
  {
    "id": "CBUM_39",
    "name": "Áo Thun Gym Oversize Fitman BIG BOI University Đen (Mã 39)",
    "category": "cbum",
    "categoryName": "CBUM",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Đen",
    "image": "/static/products/items/ao-gym-cbum-ma-39-big-boi-u-den.jpg",
    "badge": "CBUM",
    "badgeColor": "dark",
    "desc": "Tone Đen ngực in chữ U và BIG BOI đỏ trắng, kiểu dáng đại học thể thao Mỹ cực kỳ cuốn hút."
  },
  {
    "id": "CBUM_40",
    "name": "Áo Thun Gym Oversize Fitman Don't Be A Skinny Bitch Trắng",
    "category": "cbum",
    "categoryName": "CBUM",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Trắng",
    "image": "/static/products/items/ao-gym-cbum-ma-40-skinny-bitch-trang.jpg",
    "badge": "CBUM",
    "badgeColor": "dark",
    "desc": "Tone Trắng, lưng in vòng chữ DON'T BE A SKINNY BITCH lồng chữ ký xanh navy nghệ thuật, cực kỳ thanh lịch."
  },
  {
    "id": "CBUM_43",
    "name": "Áo Thun Gym Oversize Fitman CBUM Never Quitting Đen Washed (Mã 43)",
    "category": "cbum",
    "categoryName": "CBUM",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM Washed",
    "color": "Đen Washed",
    "image": "/static/products/items/ao-gym-cbum-ma-43-never-quitting-den.jpg",
    "badge": "CBUM",
    "badgeColor": "dark",
    "desc": "Tone Đen xám washed, ngực in BVM cổ điển, lưng in NEVER QUITTING not right now kiên cường."
  },
  {
    "id": "CBUM_44",
    "name": "Áo Thun Gym Oversize Fitman CBUM Lifting Club Trắng Mint (Mã 44)",
    "category": "cbum",
    "categoryName": "CBUM",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Trắng",
    "image": "/static/products/items/ao-gym-cbum-ma-44-lifting-club-trang.jpg",
    "badge": "CBUM",
    "badgeColor": "dark",
    "desc": "Tone Trắng, ngực gắn tag BUM, lưng in chữ uốn lượn Lifting Club màu xanh mint thanh thoát tươi mát."
  },
  {
    "id": "CBUM_45",
    "name": "Áo Thun Gym Oversize Fitman CBUM 5 Vết Cào 3VM Đen Washed (Mã 45)",
    "category": "cbum",
    "categoryName": "CBUM",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM Washed",
    "color": "Đen Washed",
    "image": "/static/products/items/ao-gym-cbum-ma-45-champion-claw-den.jpg",
    "badge": "CBUM",
    "badgeColor": "dark",
    "desc": "Ngực in CHAMPION BVM MENTALITY, sau lưng 5 vệt cào trắng cào xé cùng logo 3VM sắc sảo đầy uy lực."
  },
  {
    "id": "CBUM_46",
    "name": "Áo Thun Gym Oversize Fitman Don't Be A Skinny Bitch Nâu (Mã 46)",
    "category": "cbum",
    "categoryName": "CBUM",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Nâu Đậm",
    "image": "/static/products/items/ao-gym-cbum-ma-46-skinny-bitch-nau.jpg",
    "badge": "CBUM",
    "badgeColor": "dark",
    "desc": "Tone Nâu đậm, lưng in câu slogan phòng gym huyền thoại Don't Be A Skinny Bitch - Champion Mentality."
  },
  {
    "id": "CBUM_47",
    "name": "Áo Thun Gym Oversize Fitman BUMSTEAD Olympia 5X Champion Đen (Mã 47)",
    "category": "cbum",
    "categoryName": "CBUM",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM Washed",
    "color": "Đen Washed",
    "image": "/static/products/items/ao-gym-cbum-ma-47-olympia-3-den.jpg",
    "badge": "CBUM",
    "badgeColor": "dark",
    "desc": "2 mặt in BUMSTEAD OLYMPIA 3 xanh lơ viền trắng, liệt kê các năm vô địch Olympia 2019-2023 vinh quang."
  },
  {
    "id": "WOLVES_01",
    "name": "Áo Thun Gym Oversize Fitman Wolves Punisher Skull Đen (Mã W1)",
    "category": "wolves",
    "categoryName": "Wolves",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Đen",
    "image": "/static/products/items/ao-gym-wolves-w1-punisher-den.jpg",
    "badge": "WOLVES",
    "badgeColor": "orange",
    "desc": "Ngực in Đầu Lâu Trừng Phạt Punisher trắng phong cách rực cháy, bên hông logo Wolves Club gai góc."
  },
  {
    "id": "WOLVES_02",
    "name": "Áo Thun Gym Oversize Fitman Wolves Punisher Skull Nâu (Mã W2)",
    "category": "wolves",
    "categoryName": "Wolves",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Nâu Đậm",
    "image": "/static/products/items/ao-gym-wolves-w2-punisher-nau.jpg",
    "badge": "WOLVES",
    "badgeColor": "orange",
    "desc": "Tone Nâu đất thời thượng, ngực in Đầu Lâu Punisher trắng viền cọ xước sắc lẹm tôn trọn cơ bắp."
  },
  {
    "id": "WOLVES_03",
    "name": "Áo Thun Gym Oversize Fitman Wolves Akatsuki Mây Đỏ Xanh Lá (Mã W3)",
    "category": "wolves",
    "categoryName": "Wolves",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Xanh Lá Đậm",
    "image": "/static/products/items/ao-gym-wolves-w3-akatsuki-xanh-la.jpg",
    "badge": "WOLVES",
    "badgeColor": "orange",
    "desc": "Tone Xanh lá rêu độc đáo, lưng in Sói Wolves gầm thét vây quanh bởi những đám mây đỏ Akatsuki cá tính."
  },
  {
    "id": "WOLVES_04",
    "name": "Áo Thun Gym Oversize Fitman Wolves Akatsuki Mây Đỏ Nâu Cafe (Mã W4)",
    "category": "wolves",
    "categoryName": "Wolves",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Nâu Cafe",
    "image": "/static/products/items/ao-gym-wolves-w4-akatsuki-nau.jpg",
    "badge": "WOLVES",
    "badgeColor": "orange",
    "desc": "Tone Nâu cafe vintage, lưng in đại cảnh Sói Wolves mây đỏ Akatsuki phong cách gym anime đỉnh cao."
  },
  {
    "id": "WOLVES_06",
    "name": "Áo Thun Gym Oversize Fitman Wolves Akatsuki Mây Đỏ Đen (Mã W6)",
    "category": "wolves",
    "categoryName": "Wolves",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Đen",
    "image": "/static/products/items/ao-gym-wolves-w6-akatsuki-den.jpg",
    "badge": "WOLVES",
    "badgeColor": "orange",
    "desc": "Lưng in Sói Wolves gầm thét phối cùng đám mây đỏ Akatsuki trên nền áo đen, mẫu áo đắt khách nhất dòng Wolves."
  },
  {
    "id": "WOLVES_07",
    "name": "Áo Thun Gym Oversize Fitman Wolves SSDDNFGD Đen (Mã W7)",
    "category": "wolves",
    "categoryName": "Wolves",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Đen",
    "image": "/static/products/items/ao-gym-wolves-w7-ssddnfgd-den.jpg",
    "badge": "WOLVES",
    "badgeColor": "orange",
    "desc": "Ngực in Wolves nhỏ, lưng in dải ruy băng đỏ lửa WOLVES SSDDNFGD 2024 đậm chất punk rock đường phố."
  },
  {
    "id": "WOLVES_07_WHITE",
    "name": "Áo Thun Gym Oversize Fitman Wolves SSDDNFGD Trắng (Mã W7 Trắng)",
    "category": "wolves",
    "categoryName": "Wolves",
    "price": 150000,
    "fabric": "Cotton 100% 260GSM",
    "color": "Trắng",
    "image": "/static/products/items/ao-gym-wolves-w7-ssddnfgd-trang.jpg",
    "badge": "WOLVES",
    "badgeColor": "orange",
    "desc": "Phiên bản Trắng tinh khôi của mẫu Wolves SSDDNFGD ruy băng đỏ cam rực rỡ, năng động trẻ trung."
  },
  {
    "id": "SHORT_Q1",
    "name": "Quần Đùi Tập Gym Fitman CBUM Pro Short Đen (Mã Q1)",
    "category": "quan",
    "categoryName": "Quần Đùi Gym",
    "price": 150000,
    "fabric": "Dù co giãn 4 chiều",
    "color": "Đen",
    "image": "/static/products/items/quan-short-gym-cbum-q1-pro-den.jpg",
    "badge": "PRO SHORT",
    "badgeColor": "orange",
    "desc": "Chất vải dù co giãn chuyên dụng tập squat và leg day, ống xẻ tà tôn cơ đùi, đùi in số 3 trắng sắc sảo."
  },
  {
    "id": "SHORT_Q2",
    "name": "Quần Đùi Tập Gym Fitman CBUM Pro Short Trắng (Mã Q2)",
    "category": "quan",
    "categoryName": "Quần Đùi Gym",
    "price": 150000,
    "fabric": "Dù co giãn 4 chiều",
    "color": "Trắng",
    "image": "/static/products/items/quan-short-gym-cbum-q2-pro-trang.jpg",
    "badge": "PRO SHORT",
    "badgeColor": "orange",
    "desc": "Tone Trắng thể thao, đùi in số 3 xanh lơ mát mắt, xẻ tà thoáng khí tối đa khi tập nặng."
  },
  {
    "id": "SHORT_Q3",
    "name": "Quần Đùi Tập Gym Fitman CBUM Training Short Đen In Số 3 (Mã Q3)",
    "category": "quan",
    "categoryName": "Quần Đùi Gym",
    "price": 150000,
    "fabric": "Cotton thun nỉ da cá co giãn",
    "color": "Đen",
    "image": "/static/products/items/quan-short-gym-cbum-q3-training-den.jpg",
    "badge": "PRO SHORT",
    "badgeColor": "orange",
    "desc": "Vải cotton da cá dày dặn êm ái, đùi in số 3 trắng to bản, form ngắn ngang đùi hỗ trợ tối đa bài tập Squat & Deadlift."
  },
  {
    "id": "SHORT_Q4",
    "name": "Quần Đùi Tập Gym Fitman Bum Lifting Club Short Trắng (Mã Q4)",
    "category": "quan",
    "categoryName": "Quần Đùi Gym",
    "price": 150000,
    "fabric": "Dù co giãn 4 chiều",
    "color": "Trắng",
    "image": "/static/products/items/quan-short-gym-cbum-q4-blc-trang.jpg",
    "badge": "PRO SHORT",
    "badgeColor": "orange",
    "desc": "Tone Trắng thể thao cao cấp, đùi in chữ ký nghệ thuật Bum Lifting Club, tôn cơ đùi vạm vỡ và bắp chân săn chắc."
  },
  {
    "id": "SHORT_Q6",
    "name": "Quần Đùi Lưới Tập Gym Fitman Mesh Short Số 3 Kem Cát (Mã Q6)",
    "category": "quan",
    "categoryName": "Quần Đùi Gym",
    "price": 150000,
    "fabric": "Lưới Mesh 2 lớp thoáng khí",
    "color": "Kem Cát",
    "image": "/static/products/items/quan-short-gym-cbum-q6-luoi-kem.jpg",
    "badge": "PRO SHORT",
    "badgeColor": "orange",
    "desc": "Vải lưới 2 lớp cao cấp siêu nhẹ, đùi in số 3 đen, form ngắn trên gối chuẩn phong cách thể hình hiện đại."
  },
  {
    "id": "SHORT_Q7",
    "name": "Quần Đùi Lưới Tập Gym Fitman Mesh Short BIG BOI Đen (Mã Q7)",
    "category": "quan",
    "categoryName": "Quần Đùi Gym",
    "price": 150000,
    "fabric": "Lưới Mesh 2 lớp thoáng khí",
    "color": "Đen",
    "image": "/static/products/items/quan-short-gym-cbum-q7-luoi-big-boi-den.jpg",
    "badge": "PRO SHORT",
    "badgeColor": "orange",
    "desc": "Tone Đen cá tính, đùi in chữ BIG BOI UNIVERSITY, thoáng mồ hôi cực nhanh, có túi hai bên sâu tiện lợi."
  },
  {
    "id": "NHOM_1",
    "name": "Bộ Sưu Tập Áo CBUM Olympia Dòng 1",
    "category": "group",
    "categoryName": "Bảng Mã Tổng Hợp",
    "price": 150000,
    "fabric": "100% Cotton 260GSM",
    "color": "Nhiều màu",
    "image": "/static/products/nhom_1.jpg",
    "badge": "BEST SELLER",
    "badgeColor": "dark",
    "desc": "Gồm các mã hot: 1, 4, 5, 6, 15, 16, 17, 19, 20. Bảng số mã rõ nét giúp dễ đối chiếu."
  },
  {
    "id": "NHOM_2",
    "name": "Bộ Sưu Tập Áo CBUM Standard Dòng 2",
    "category": "group",
    "categoryName": "Bảng Mã Tổng Hợp",
    "price": 150000,
    "fabric": "100% Cotton 260GSM",
    "color": "Nhiều màu",
    "image": "/static/products/nhom_2.jpg",
    "badge": "POPULAR",
    "badgeColor": "dark",
    "desc": "Gồm các mã: 2, 3, 7, 8, 9, 10, 11, 12, 14. Thiết kế đa dạng dễ phối đồ đi tập hoặc đi chơi."
  },
  {
    "id": "NHOM_3",
    "name": "Quần Đùi Tập Gym CBUM Pro Short Tổng Hợp",
    "category": "group",
    "categoryName": "Bảng Mã Tổng Hợp",
    "price": 150000,
    "fabric": "Dù co giãn 4 chiều",
    "color": "Nhiều màu",
    "image": "/static/products/nhom_3.jpg",
    "badge": "PRO SHORT",
    "badgeColor": "orange",
    "desc": "Gồm mã Q1, Q2, Q3, Q4: Thiết kế xẻ tà đùi tối ưu squat và leg day, thoáng khí."
  },
  {
    "id": "NHOM_4",
    "name": "Bộ Sưu Tập Áo Wolves & Skull Punisher Tổng Hợp",
    "category": "group",
    "categoryName": "Bảng Mã Tổng Hợp",
    "price": 150000,
    "fabric": "100% Cotton 260GSM",
    "color": "Nhiều màu",
    "image": "/static/products/nhom_4.jpg",
    "badge": "WOLVES STYLE",
    "badgeColor": "orange",
    "desc": "Gồm các mã W1, W2, W7, 28, 29 tone Nâu, Trắng, Đen, Be thể thao mạnh mẽ."
  },
  {
    "id": "NHOM_5",
    "name": "Bộ Sưu Tập Champion Mentality & Big Boi Tổng Hợp",
    "category": "group",
    "categoryName": "Bảng Mã Tổng Hợp",
    "price": 150000,
    "fabric": "100% Cotton 260GSM",
    "color": "Nhiều màu",
    "image": "/static/products/nhom_5.jpg",
    "badge": "HOT COMBO",
    "badgeColor": "dark",
    "desc": "Gồm mã áo 30, 31, 32, 34, 35, 36, 39 kết hợp cùng quần short thể thao Q6, Q7 đồng bộ."
  },
  {
    "id": "NHOM_6",
    "name": "Bộ Sưu Tập Áo Never Quitting Olympia Tổng Hợp",
    "category": "group",
    "categoryName": "Bảng Mã Tổng Hợp",
    "price": 150000,
    "fabric": "100% Cotton 260GSM",
    "color": "Nhiều màu",
    "image": "/static/products/nhom_6.jpg",
    "badge": "CBUM 5X",
    "badgeColor": "dark",
    "desc": "Gồm các mã 43, 44, 45, 46, 47 truyền cảm hứng tập luyện bền bỉ, tôn form vai xô."
  },
  {
    "id": "MAU_MOI_1",
    "name": "Bộ Sưu Tập Mẫu Mới 2026 — Tone Trắng & Kem Cát",
    "category": "group",
    "categoryName": "Bảng Mã Tổng Hợp",
    "price": 150000,
    "fabric": "100% Cotton 260GSM",
    "color": "Trắng / Kem Cát",
    "image": "/static/products/mau_moi_1.png",
    "badge": "MẪU MỚI 2026",
    "badgeColor": "orange",
    "desc": "Tone Trắng / Kem cát sang trọng dệt 2 chiều, đứng form vai ngực tôn dáng gymer."
  },
  {
    "id": "MAU_MOI_2",
    "name": "Bộ Sưu Tập Mẫu Mới 2026 — Tone Đen Huyền Bí",
    "category": "group",
    "categoryName": "Bảng Mã Tổng Hợp",
    "price": 150000,
    "fabric": "100% Cotton 260GSM",
    "color": "Đen",
    "image": "/static/products/mau_moi_2.png",
    "badge": "MẪU MỚI 2026",
    "badgeColor": "orange",
    "desc": "Tone Đen cá tính, họa tiết graphic thể thao sắc nét, che khuyết điểm tôn cơ bắp."
  }
];

let currentCategory = 'all';
let currentSearch = '';
let visibleCount = 16;
const PAGE_SIZE = 16;

function initCatalog() {
  const grid = document.getElementById('productGrid');
  const tabBtns = document.querySelectorAll('.tab-btn');
  const searchInput = document.getElementById('catalogSearchInput');
  const clearBtn = document.getElementById('catalogSearchClear');
  const loadMoreBtn = document.getElementById('loadMoreBtn');
  const loadMoreContainer = document.getElementById('loadMoreContainer');
  const loadMoreText = document.getElementById('loadMoreText');

  // Update tab counters based on brand categories
  const countAll = PRODUCTS.filter(p => p.category !== 'group').length;
  const countCbum = PRODUCTS.filter(p => p.category === 'cbum').length;
  const countRaw = PRODUCTS.filter(p => p.category === 'raw').length;
  const countYoungla = PRODUCTS.filter(p => p.category === 'youngla').length;
  const countWolves = PRODUCTS.filter(p => p.category === 'wolves').length;
  const countQuan = PRODUCTS.filter(p => p.category === 'quan').length;

  const elCountAll = document.getElementById('tabCountAll');
  const elCountCbum = document.getElementById('tabCountCbum');
  const elCountRaw = document.getElementById('tabCountRaw');
  const elCountYoungla = document.getElementById('tabCountYoungla');
  const elCountWolves = document.getElementById('tabCountWolves');
  const elCountQuan = document.getElementById('tabCountQuan');

  if (elCountAll) elCountAll.textContent = countAll;
  if (elCountCbum) elCountCbum.textContent = countCbum;
  if (elCountRaw) elCountRaw.textContent = countRaw;
  if (elCountYoungla) elCountYoungla.textContent = countYoungla;
  if (elCountWolves) elCountWolves.textContent = countWolves;
  if (elCountQuan) elCountQuan.textContent = countQuan;

  if (!grid) return;

  function getFilteredProducts() {
    let list = PRODUCTS;
    if (currentCategory === 'all') {
      list = PRODUCTS.filter(p => p.category !== 'group');
    } else {
      list = PRODUCTS.filter(p => p.category === currentCategory);
    }

    if (currentSearch.trim()) {
      const q = currentSearch.toLowerCase().trim();
      list = list.filter(p => {
        return (p.name && p.name.toLowerCase().includes(q)) ||
               (p.id && p.id.toLowerCase().includes(q)) ||
               (p.color && p.color.toLowerCase().includes(q)) ||
               (p.fabric && p.fabric.toLowerCase().includes(q)) ||
               (p.desc && p.desc.toLowerCase().includes(q)) ||
               (p.categoryName && p.categoryName.toLowerCase().includes(q)) ||
               (p.category && p.category.toLowerCase().includes(q));
      });
    }
    return list;
  }

  function render() {
    const filtered = getFilteredProducts();
    const visibleProducts = filtered.slice(0, visibleCount);

    if (filtered.length === 0) {
      grid.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 60px 20px; color: #71717A;">
          <p style="font-size: 1.2rem; font-weight: 600; margin-bottom: 8px;">Không tìm thấy sản phẩm phù hợp</p>
          <p style="font-size: 0.9rem;">Thử tìm kiếm với từ khóa khác hoặc bấm nút "Tất Cả" nhé!</p>
        </div>
      `;
      if (loadMoreContainer) loadMoreContainer.style.display = 'none';
      return;
    }

    grid.innerHTML = visibleProducts.map(p => `
      <article class="product-card" data-id="${p.id}" data-category="${p.category}">
        <div class="product-media" onclick="openLightbox('${p.image}', '${p.name.replace(/'/g, "\'")}')">
          <img src="${p.image}" alt="${p.name} - Fitman Sportswear" loading="lazy" width="300" height="330" />
          <div class="product-badges">
            <span class="badge badge-${p.badgeColor || 'orange'}">${p.badge}</span>
            ${p.color ? `<span class="badge badge-dark" style="background: rgba(0,0,0,0.68); font-size: 0.72rem;">${p.color}</span>` : ''}
          </div>
        </div>
        <div class="product-body">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">
            <span class="product-category">${p.categoryName}</span>
            <span style="font-size: 0.75rem; font-weight: 700; color: #A1A1AA;">MÃ: ${p.id}</span>
          </div>
          <h3 class="product-name">${p.name}</h3>
          <p class="product-meta"><strong>Vải:</strong> ${p.fabric}</p>
          <p style="font-size: 0.8rem; color: #71717A; line-height: 1.4; margin-bottom: 12px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">${p.desc || ''}</p>
          <div class="product-pricing">
            <span class="price-current">${formatMoney(p.price)}</span>
            <span class="price-unit">/ cái</span>
          </div>
          <div class="product-actions">
            <button class="btn btn-primary btn-add-cart" onclick="addToCart('${p.id}')">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"></path><line x1="3" y1="6" x2="21" y2="6"></line><path d="M16 10a4 4 0 0 1-8 0"></path></svg>
              Chọn Mua
            </button>
            <button class="btn-zoom" title="Xem ảnh to" onclick="openLightbox('${p.image}', '${p.name.replace(/'/g, "\'")}')">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line><line x1="11" y1="8" x2="11" y2="14"></line><line x1="8" y1="11" x2="14" y2="11"></line></svg>
            </button>
          </div>
        </div>
      </article>
    `).join('');

    if (loadMoreContainer) {
      if (visibleCount < filtered.length) {
        loadMoreContainer.style.display = 'block';
        const remaining = filtered.length - visibleCount;
        if (loadMoreText) {
          loadMoreText.textContent = `Xem Thêm Mẫu Hot (còn ${remaining} mẫu) 👇`;
        }
      } else {
        loadMoreContainer.style.display = 'none';
      }
    }
  }

  // Tab switching
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentCategory = btn.dataset.category;
      visibleCount = PAGE_SIZE;
      render();
    });
  });

  // Search input
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      currentSearch = e.target.value;
      visibleCount = PAGE_SIZE;
      if (clearBtn) {
        clearBtn.style.display = currentSearch ? 'block' : 'none';
      }
      render();
    });
  }

  // Clear search button
  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      if (searchInput) searchInput.value = '';
      currentSearch = '';
      clearBtn.style.display = 'none';
      visibleCount = PAGE_SIZE;
      render();
    });
  }

  // Load more button
  if (loadMoreBtn) {
    loadMoreBtn.addEventListener('click', () => {
      visibleCount += PAGE_SIZE;
      render();
    });
  }

  render();
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
    1: { price: 180000, desc: "1 áo 150.000đ + 30.000đ tiền ship COD toàn quốc", benefit: "💡 Mua từ 2 áo để nhận FREESHIP!" },
    2: { price: 299000, desc: "2 áo giá 299.000đ — MIỄN PHÍ VẬN CHUYỂN TOÀN QUỐC", benefit: "🔥 Tiết kiệm 61.000đ so với mua lẻ!" },
    3: { price: 399000, desc: "3 áo giá 399.000đ — MIỄN PHÍ VẬN CHUYỂN TOÀN QUỐC", benefit: "🔥 Thêm áo thứ 3 chỉ tốn đúng 100k!" },
    4: { price: 520000, desc: "4 áo giá 520.000đ — MIỄN PHÍ VẬN CHUYỂN TOÀN QUỐC", benefit: "🔥 Đồng giá sỉ 130k/áo từ cái thứ 4!" },
    5: { price: 650000, desc: "5 áo giá 650.000đ — MIỄN PHÍ VẬN CHUYỂN TOÀN QUỐC", benefit: "🔥 Đồng giá sỉ 130k/áo + FREESHIP!" }
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
   3. SMART SIZE FINDER (UPGRADE: XXL & CÓ BỤNG UP SIZE)
   =================================================================== */
let currentRecommendedSize = 'M';
let hasBellySelected = false;

function selectBellyOption(hasBelly) {
  hasBellySelected = Boolean(hasBelly);
  const normalCard = document.getElementById('bellyOptNormalCard');
  const beerCard = document.getElementById('bellyOptBeerCard');
  const bellyText = document.getElementById('bellyStatusText');
  const normalInput = document.getElementById('bellyOptNormal');
  const beerInput = document.getElementById('bellyOptBeer');

  if (normalCard && beerCard) {
    if (hasBellySelected) {
      normalCard.classList.remove('active');
      beerCard.classList.add('active');
      if (beerInput) beerInput.checked = true;
      if (bellyText) bellyText.textContent = "Có bụng / Bụng bia (+1 Size)";
    } else {
      beerCard.classList.remove('active');
      normalCard.classList.add('active');
      if (normalInput) normalInput.checked = true;
      if (bellyText) bellyText.textContent = "Bình thường / Cơ bắp";
    }
  }

  if (typeof window.updateSizeFinderCalculation === 'function') {
    window.updateSizeFinderCalculation();
  }
}

function applyRecommendedSizeToShop() {
  const btn = document.getElementById('applySizeBtn');
  if (btn) {
    const originalText = btn.innerHTML;
    btn.innerHTML = `✓ Đã Chọn Size ${currentRecommendedSize}!`;
    btn.style.background = '#10B981';
    btn.style.borderColor = '#10B981';
    setTimeout(() => {
      btn.innerHTML = originalText;
      btn.style.background = '';
      btn.style.borderColor = '';
    }, 2000);
  }

  // Update existing cart items if any
  if (cartItems.length > 0) {
    cartItems.forEach(item => { item.size = currentRecommendedSize; });
    renderCart();
  }
}

function initSizeFinder() {
  const heightSlider = document.getElementById('heightSlider');
  const weightSlider = document.getElementById('weightSlider');
  const heightVal = document.getElementById('heightVal');
  const weightVal = document.getElementById('weightVal');
  const sizeOutput = document.getElementById('sizeOutput');
  const sizeAdvice = document.getElementById('sizeAdvice');
  const sizeBellyNote = document.getElementById('sizeBellyNote');

  if (!heightSlider || !weightSlider) return;

  window.updateSizeFinderCalculation = function calculateSize() {
    const h = parseInt(heightSlider.value, 10);
    const w = parseInt(weightSlider.value, 10);

    if (heightVal) heightVal.textContent = `${h} cm`;
    if (weightVal) weightVal.textContent = `${w} kg`;

    let baseSize = 'M';
    let baseAdvice = '';

    // Phân loại size chuẩn theo cân nặng & chiều cao (chuẩn form CBUM Oversize)
    if (w < 62) {
      baseSize = 'S';
      baseAdvice = `Với cân nặng ${w}kg, Size S là kích thước chuẩn tôn vai xô mà vẫn rộng rãi thoải mái.`;
    } else if (w <= 72) {
      baseSize = 'M';
      baseAdvice = `Với chiều cao ${h}cm và ${w}kg, Size M là form chuẩn đẹp nhất tôn cơ bắp ngực và lưng.`;
    } else if (w <= 83) {
      baseSize = 'L';
      baseAdvice = `Thể hình vạm vỡ (${w}kg), Size L chuẩn form CBUM phủ mông, tay áo che bắp tay cực đẹp.`;
    } else if (w <= 94) {
      baseSize = 'XL';
      baseAdvice = `Cân nặng ${w}kg mặc Size XL cực kỳ phong cách, rộng rãi đúng chuẩn streetwear thể thao.`;
    } else {
      baseSize = 'XXL';
      baseAdvice = `Cân nặng ${w}kg, Fitman có Size XXL siêu rộng rãi phủ mông chuẩn form gymer quốc tế.`;
    }

    let recommendedSize = baseSize;
    let adviceText = baseAdvice;

    // Nếu chọn có bụng / bụng bia: TỰ ĐỘNG UP 1 SIZE
    if (hasBellySelected) {
      const sizeUpMap = {
        'S': 'M',
        'M': 'L',
        'L': 'XL',
        'XL': 'XXL',
        'XXL': 'XXL'
      };
      recommendedSize = sizeUpMap[baseSize] || 'XXL';

      if (baseSize === 'XXL') {
        adviceText = `⚡ Dáng người có bụng (${w}kg): Fitman khuyên bạn chọn Size XXL lớn nhất để vạt áo rủ suông tự nhiên, hoàn toàn che khuyết điểm vòng 2!`;
      } else {
        adviceText = `⚡ Bạn chọn "Có bụng": Fitman đã tự động UP 1 SIZE (từ Size ${baseSize} lên ${recommendedSize}) giúp form áo suông rủ, thoải mái cử động và che bụng bia hoàn hảo!`;
      }

      if (sizeBellyNote) {
        sizeBellyNote.textContent = `✓ Đã tự động tăng 1 size che bụng (${baseSize} ➜ ${recommendedSize})`;
        sizeBellyNote.style.color = '#FF7A1A';
        sizeBellyNote.style.fontWeight = '700';
      }
    } else {
      if (sizeBellyNote) {
        sizeBellyNote.textContent = 'Form Oversize phủ mông nhẹ, che khuyết điểm bụng và lưng';
        sizeBellyNote.style.color = 'var(--text-sub)';
        sizeBellyNote.style.fontWeight = 'normal';
      }
    }

    currentRecommendedSize = recommendedSize;
    if (sizeOutput) sizeOutput.textContent = recommendedSize;
    if (sizeAdvice) sizeAdvice.textContent = adviceText;
  };

  heightSlider.addEventListener('input', window.updateSizeFinderCalculation);
  weightSlider.addEventListener('input', window.updateSizeFinderCalculation);
  window.updateSizeFinderCalculation();
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

  const chosenSize = currentRecommendedSize || 'L';
  const existing = cartItems.find(item => item.id === productId && item.size === chosenSize);
  if (existing) {
    existing.qty += 1;
  } else {
    cartItems.push({ ...prod, qty: 1, size: chosenSize });
  }

  updateCartBadge();
  openCart();
}

function updateCartQtyByIndex(index, delta) {
  if (!cartItems[index]) return;
  cartItems[index].qty += delta;
  if (cartItems[index].qty <= 0) {
    cartItems.splice(index, 1);
  }
  updateCartBadge();
  renderCart();
}

function updateCartItemSize(index, newSize) {
  if (!cartItems[index]) return;
  cartItems[index].size = newSize;
  renderCart();
}

function updateCartBadge() {
  const badge = document.getElementById('cartBadge');
  const totalQty = cartItems.reduce((sum, item) => sum + item.qty, 0);
  if (badge) badge.textContent = totalQty;
}

function calculateOrderTotals() {
  const totalQty = cartItems.reduce((sum, item) => sum + item.qty, 0);
  let subtotal = 0;
  let shippingFee = 0;
  let grandTotal = 0;

  if (totalQty === 1) {
    subtotal = 150000;
    shippingFee = 30000;
    grandTotal = 180000;
  } else if (totalQty === 2) {
    subtotal = 299000;
    shippingFee = 0;
    grandTotal = 299000;
  } else if (totalQty === 3) {
    subtotal = 399000;
    shippingFee = 0;
    grandTotal = 399000;
  } else if (totalQty >= 4) {
    subtotal = totalQty * 130000;
    shippingFee = 0;
    grandTotal = subtotal;
  }

  return { totalQty, subtotal, shippingFee, grandTotal };
}

function renderCart() {
  const body = document.getElementById('cartBody');
  const totalElem = document.getElementById('cartTotal');
  const discountElem = document.getElementById('cartDiscountInfo');
  if (!body) return;

  const { totalQty, subtotal, shippingFee, grandTotal } = calculateOrderTotals();

  if (cartItems.length === 0) {
    body.innerHTML = `
      <div class="cart-empty" style="text-align: center; padding: 40px 16px; color: #71717A;">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#D4D4D8" stroke-width="1.5" style="margin: 0 auto;"><circle cx="9" cy="21" r="1"></circle><circle cx="20" cy="21" r="1"></circle><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path></svg>
        <p style="margin-top: 12px; font-weight: 500;">Giỏ hàng của bạn đang trống</p>
        <a href="#catalog" onclick="closeCart()" class="btn btn-outline" style="margin-top: 16px; font-size: 0.85rem;">Khám phá mẫu ngay</a>
      </div>
    `;
    if (totalElem) totalElem.textContent = "0đ";
    if (discountElem) discountElem.textContent = "Thêm 2 áo để được FREESHIP";
    return;
  }

  let discountNote = "";
  if (totalQty === 1) {
    discountNote = "Phí ship 30k. Thêm 1 món nữa để được FREESHIP!";
  } else if (totalQty === 2) {
    discountNote = "🎉 Bạn được FREESHIP toàn quốc! Thêm 1 món chỉ thêm 100k!";
  } else if (totalQty === 3) {
    discountNote = "🎉 Bạn được FREESHIP toàn quốc! Combo 3 món siêu tiết kiệm!";
  } else if (totalQty >= 4) {
    discountNote = `🎉 Đồng giá sỉ ${formatMoney(130000)}/món + FREESHIP toàn quốc!`;
  }

  body.innerHTML = cartItems.map((item, idx) => `
    <div style="display: flex; gap: 12px; padding-bottom: 12px; border-bottom: 1px solid #F4F4F5; align-items: center;">
      <img src="${item.image}" alt="${item.name}" style="width: 58px; height: 58px; object-fit: cover; border-radius: 8px; flex-shrink: 0;" />
      <div style="flex-grow: 1; min-width: 0;">
        <h4 style="font-size: 0.86rem; font-weight: 700; color: #18181B; margin-bottom: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${item.name}</h4>
        <div style="display: flex; align-items: center; gap: 8px; margin-top: 4px;">
          <span style="font-size: 0.82rem; color: #FF7A1A; font-weight: 700;">150.000đ</span>
          <div style="display: inline-flex; align-items: center; gap: 4px;">
            <label style="font-size: 0.72rem; color: #71717A;">Size:</label>
            <select onchange="updateCartItemSize(${idx}, this.value)" style="padding: 2px 6px; border: 1px solid #D4D4D8; border-radius: 4px; font-size: 0.75rem; font-weight: 700; background: #FFF; cursor: pointer; color: #18181B;">
              <option value="S" ${item.size === 'S' ? 'selected' : ''}>S (<62kg)</option>
              <option value="M" ${item.size === 'M' ? 'selected' : ''}>M (62-72kg)</option>
              <option value="L" ${item.size === 'L' ? 'selected' : ''}>L (73-83kg)</option>
              <option value="XL" ${item.size === 'XL' ? 'selected' : ''}>XL (84-94kg)</option>
              <option value="XXL" ${item.size === 'XXL' ? 'selected' : ''}>XXL (>94kg / Có bụng)</option>
            </select>
          </div>
        </div>
      </div>
      <div style="display: flex; align-items: center; gap: 6px; flex-shrink: 0;">
        <button onclick="updateCartQtyByIndex(${idx}, -1)" style="width: 24px; height: 24px; background: #F4F4F5; border-radius: 4px; font-weight: bold; cursor: pointer; border: none;">-</button>
        <span style="font-weight: 600; font-size: 0.88rem; min-width: 16px; text-align: center;">${item.qty}</span>
        <button onclick="updateCartQtyByIndex(${idx}, 1)" style="width: 24px; height: 24px; background: #F4F4F5; border-radius: 4px; font-weight: bold; cursor: pointer; border: none;">+</button>
      </div>
    </div>
  `).join('');

  if (totalElem) totalElem.textContent = formatMoney(grandTotal);
  if (discountElem) discountElem.textContent = discountNote;
}

function formatMoney(amount) {
  return Number(amount || 0).toLocaleString('vi-VN') + 'đ';
}

function proceedToCheckout() {
  openQuickOrderModal();
}

/* ===================================================================
   FAST CHECKOUT MODAL HANDLERS
   =================================================================== */
let currentPaymentMethod = 'COD';

function selectPaymentMethod(method) {
  currentPaymentMethod = method;

  const tabs = {
    'COD': document.getElementById('payTabCod'),
    'TECHCOMBANK': document.getElementById('payTabTechcom'),
    'MOMO': document.getElementById('payTabMomo')
  };
  const details = {
    'COD': document.getElementById('payDetailsCod'),
    'TECHCOMBANK': document.getElementById('payDetailsTechcom'),
    'MOMO': document.getElementById('payDetailsMomo')
  };

  Object.keys(tabs).forEach(k => {
    if (tabs[k]) {
      if (k === method) tabs[k].classList.add('active');
      else tabs[k].classList.remove('active');
    }
  });

  Object.keys(details).forEach(k => {
    if (details[k]) {
      details[k].style.display = (k === method) ? 'block' : 'none';
    }
  });
}

function openQuickOrderModal() {
  if (cartItems.length === 0) {
    alert("Giỏ hàng của bạn đang trống! Vui lòng chọn ít nhất 1 sản phẩm để đặt hàng.");
    return;
  }
  closeCart();

  const { totalQty, subtotal, shippingFee, grandTotal } = calculateOrderTotals();

  // Populate items list
  const listElem = document.getElementById('quickOrderItemsList');
  if (listElem) {
    listElem.innerHTML = cartItems.map(item => `
      <div style="display: flex; gap: 10px; align-items: center; background: #FFFFFF; padding: 8px 12px; border-radius: 6px; border: 1px solid #E4E4E7;">
        <img src="${item.image}" alt="${item.name}" style="width: 44px; height: 44px; object-fit: cover; border-radius: 6px; flex-shrink: 0;" />
        <div style="flex-grow: 1; min-width: 0;">
          <div style="font-size: 0.85rem; font-weight: 700; color: #18181B; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${item.name}</div>
          <div style="font-size: 0.75rem; color: #71717A;">
            Size: <strong style="color: #FF7A1A;">${item.size || 'L'}</strong> • Số lượng: <strong>x${item.qty}</strong>
          </div>
        </div>
        <strong style="font-size: 0.88rem; color: #18181B; flex-shrink: 0;">${formatMoney(150000 * item.qty)}</strong>
      </div>
    `).join('');
  }

  // Populate summary
  const qtyElem = document.getElementById('quickOrderQty');
  const subtotalElem = document.getElementById('quickOrderSubtotal');
  const shippingElem = document.getElementById('quickOrderShipping');
  const grandTotalElem = document.getElementById('quickOrderGrandTotal');
  const tcbAmountElem = document.getElementById('tcbAmountText');
  const qrImgElem = document.getElementById('quickOrderVietqrImg');

  if (qtyElem) qtyElem.textContent = totalQty;
  if (subtotalElem) subtotalElem.textContent = formatMoney(subtotal);
  if (shippingElem) {
    shippingElem.textContent = shippingFee === 0 ? "0đ (Freeship toàn quốc)" : "30.000đ";
    shippingElem.style.color = shippingFee === 0 ? "#10B981" : "#18181B";
  }
  if (grandTotalElem) grandTotalElem.textContent = formatMoney(grandTotal);

  if (tcbAmountElem) {
    tcbAmountElem.textContent = formatMoney(grandTotal);
    tcbAmountElem.setAttribute('data-raw', grandTotal);
  }

  // Update Techcombank QR code
  if (qrImgElem) {
    const qrUrl = `https://img.vietqr.io/image/TCB-3386111168-compact2.png?amount=${grandTotal}&addInfo=FITMAN%20ORDER&accountName=HO%20KINH%20DOANH%20CUA%20HANG%20FITMAN`;
    qrImgElem.src = qrUrl;
  }

  selectPaymentMethod('COD');

  const modal = document.getElementById('quickOrderModal');
  if (modal) {
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }
}

function closeQuickOrderModal() {
  const modal = document.getElementById('quickOrderModal');
  if (modal) {
    modal.classList.remove('active');
    document.body.style.overflow = '';
  }
}

function copyText(text, btnElem) {
  if (!text) return;
  navigator.clipboard.writeText(text).then(() => {
    if (btnElem) {
      const orig = btnElem.textContent;
      btnElem.textContent = "✓ Đã chép!";
      setTimeout(() => { btnElem.textContent = orig; }, 1800);
    }
  }).catch(() => {
    alert(`Đã sao chép: ${text}`);
  });
}

async function submitQuickOrder(event) {
  event.preventDefault();

  if (cartItems.length === 0) {
    alert("Giỏ hàng của bạn đang trống!");
    return;
  }

  const nameInput = document.getElementById('quickOrderName');
  const phoneInput = document.getElementById('quickOrderPhone');
  const addressInput = document.getElementById('quickOrderAddress');
  const noteInput = document.getElementById('quickOrderNote');
  const submitBtn = document.getElementById('quickOrderSubmitBtn');
  const statusMsg = document.getElementById('quickOrderStatusMessage');

  const customerName = nameInput ? nameInput.value.trim() : '';
  const customerPhone = phoneInput ? phoneInput.value.trim() : '';
  const shippingAddress = addressInput ? addressInput.value.trim() : '';
  const note = noteInput ? noteInput.value.trim() : '';

  if (!customerName || !customerPhone || !shippingAddress) {
    alert("Vui lòng điền đầy đủ Họ tên, Số điện thoại và Địa chỉ giao hàng!");
    return;
  }

  const { grandTotal } = calculateOrderTotals();

  const payload = {
    customer_name: customerName,
    customer_phone: customerPhone,
    shipping_address: shippingAddress,
    payment_method: currentPaymentMethod,
    items: cartItems.map(i => ({
      id: i.id,
      name: i.name,
      size: i.size || 'L',
      qty: i.qty,
      price: 150000,
      image: i.image
    })),
    total_amount: grandTotal,
    note: note
  };

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = "⏳ Đang tạo đơn hàng...";
  }

  try {
    const res = await fetch('/api/quick-order', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (data.success && data.order_id) {
      // Clear cart
      cartItems = [];
      updateCartBadge();
      renderCart();
      closeQuickOrderModal();

      // Redirect immediately to Thank You & Tracking page
      window.location.href = `/thank-you.html?order_id=${encodeURIComponent(data.order_id)}`;
    } else {
      if (statusMsg) {
        statusMsg.style.display = 'block';
        statusMsg.style.background = '#FEE2E2';
        statusMsg.style.color = '#B91C1C';
        statusMsg.textContent = data.error || "Đặt hàng thất bại. Vui lòng kiểm tra lại thông tin!";
      }
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = "🚀 XÁC NHẬN ĐẶT HÀNG NGAY";
      }
    }
  } catch (err) {
    console.error("Error submitting quick order:", err);
    if (statusMsg) {
      statusMsg.style.display = 'block';
      statusMsg.style.background = '#FEE2E2';
      statusMsg.style.color = '#B91C1C';
      statusMsg.textContent = "Không thể kết nối máy chủ. Vui lòng kiểm tra mạng hoặc thử lại!";
    }
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = "🚀 XÁC NHẬN ĐẶT HÀNG NGAY";
    }
  }
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

