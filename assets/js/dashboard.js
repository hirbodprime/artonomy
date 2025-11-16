
/* رنگ نوار پیشرفت */
(function(){
  const el=document.querySelector('.progress-inner'); if(!el) return;
  const pct=parseInt({{ completion|default:0 }}); 
  el.style.background = pct<40 ? '#f87171' : (pct<80 ? '#facc15' : 'var(--accent-2)');
})();

/* منوی کناری موبایل */
(function(){
  const side   = document.getElementById('sideNav');
  const scrim  = document.getElementById('sideScrim');
  const openBtn= document.getElementById('openSide');
  const DESKTOP = 900;
  const closeBtn = document.getElementById('closeSide');

  const toggleWrap = document.querySelector('.side-toggle');

  function setOpen(open){
    side.classList.toggle('is-open', open);
    scrim.classList.toggle('is-open', open);
    side.setAttribute('aria-hidden', (!open).toString());
    openBtn?.setAttribute('aria-expanded', open.toString());
    document.documentElement.style.overflow = open ? 'hidden' : '';

    // 🔹 hide hamburger while menu is open
    if (toggleWrap) {
      toggleWrap.style.opacity = open ? '0' : '1';
      toggleWrap.style.pointerEvents = open ? 'none' : 'auto';
    }
  }
  openBtn?.addEventListener('click', ()=> setOpen(!side.classList.contains('is-open')));
  scrim?.addEventListener('click', ()=> setOpen(false));
  document.addEventListener('keydown', e=>{ if(e.key==='Escape') setOpen(false); });
  closeBtn?.addEventListener('click', ()=> setOpen(false));

  let lastW = window.innerWidth;
  window.addEventListener('resize', ()=>{
    const w = window.innerWidth;
    if (w >= DESKTOP && lastW < DESKTOP) setOpen(false);
    lastW = w;
  });
  side?.addEventListener('click', e=>{
    if (window.innerWidth < DESKTOP && e.target.closest('a')) setOpen(false);
  });
})();

/* سوییچ بخش نقش artist/business */
(function(){
  function updateRoleUI(){
    const role=document.querySelector('[name="role"]')?.value;
    const artist=document.getElementById('artist-fields');
    const business=document.getElementById('business-fields');
    if(!artist||!business) return;
    artist.style.display = (role==='artist')?'':'none';
    business.style.display = (role==='business')?'':'none';
  }
  document.querySelector('[name="role"]')?.addEventListener('change',updateRoleUI);
  updateRoleUI();
})();

/* فیلتر زیرشاخه بر اساس دسته */
(function(){
  const SUBCAT_MAP = {{ subcat_map|safe }};
  const catSel=document.getElementById('id_category')||document.querySelector('[name="category"]');
  const subSel=document.getElementById('id_subcategory')||document.querySelector('[name="subcategory"]');
  function refill(){
    if(!catSel||!subSel) return;
    const items=SUBCAT_MAP[parseInt(catSel.value||'0')]||[];
    const current=subSel.value; subSel.innerHTML='';
    const o0=document.createElement('option'); o0.value=''; o0.textContent='— یک زیرشاخه را انتخاب کنید —'; subSel.appendChild(o0);
    for(const it of items){ const o=document.createElement('option'); o.value=it.id; o.textContent=it.name; subSel.appendChild(o); }
    if(items.some(x=>String(x.id)===current)) subSel.value=current;
  }
  catSel?.addEventListener('change',refill); refill();
})();

/* تگ حذف ردیف‌ها */
document.addEventListener('click',function(e){
  const chip=e.target.closest('[data-del]'); if(!chip) return; e.preventDefault();
  const row=chip.closest('.fsrow'); if(!row) return;
  let chk=row.querySelector('input[type="checkbox"][name$="-DELETE"]');
  if(chk){
    chk.checked=!chk.checked;
    row.classList.toggle('row-deleting',chk.checked);
    chip.textContent=chk.checked?'بازگردانی':'حذف';
    return;
  }
  const any=row.querySelector('input[name],select[name],textarea[name]'); if(!any) return;
  const m=any.name.match(/^(.*-\d+)-/); if(!m) return; const base=m[1]; const delName=base+'DELETE';
  let hidden=row.querySelector(`input[type="hidden"][name="${delName}"]`);
  if(hidden){
    hidden.remove(); row.classList.remove('row-deleting'); chip.textContent='حذف';
  } else {
    hidden=document.createElement('input'); hidden.type='hidden'; hidden.name=delName; hidden.value='on';
    row.appendChild(hidden); row.classList.add('row-deleting'); chip.textContent='بازگردانی';
  }
});

/* پیش‌نمایش زنده‌ی ورودی فایل */
// حداکثر حجم: ۱ مگابایت
const MAX_FILE_BYTES = 1 * 1024 * 1024;

function handleFileInputChange(input) {
  const file = input.files && input.files[0];

  // 🔹 محدوده منطقی برای این فیلد:
  // اول سعی می‌کنیم در گالری، بعد row، بعد formset، بعد panel
  const scope =
    input.closest('.gallery-item') ||
    input.closest('.row') ||
    input.closest('.formset') ||
    input.closest('.panel');

  if (!scope) return;

  // ارور مخصوص همین محدوده (از قبل تو HTML هست)
  const errorEl = scope.querySelector('[data-upload-error]');

  // پیدا کردن preview مناسب:
  const previews = Array.from(scope.querySelectorAll('[data-preview]'));
  let preview = null;

  if (previews.length === 1) {
    preview = previews[0];
  } else if (previews.length > 1) {
    // اگر چند تا img هست، نزدیک‌ترین img بعد از input توی DOM را انتخاب می‌کنیم
    previews.forEach(img => {
      const rel = input.compareDocumentPosition(img);
      const isAfter = rel & Node.DOCUMENT_POSITION_FOLLOWING;
      if (!preview && isAfter) {
        preview = img;
      }
    });
    // اگر هیچکدوم بعد از input نبود، اولین را می‌گیریم
    if (!preview && previews.length) {
      preview = previews[0];
    }
  }

  if (!file) {
    if (errorEl) errorEl.textContent = '';
    return;
  }

  // 🔴 چک سایز
  if (file.size > MAX_FILE_BYTES) {
    if (errorEl) {
      const mb = (file.size / (1024 * 1024)).toFixed(2);
      errorEl.textContent = `حجم فایل ${mb} مگابایت است. حداکثر مجاز ۱ مگابایت می‌باشد.`;
    }
    // پاک کردن انتخاب تا نتونه با فایل بزرگ ذخیره کنه
    input.value = '';
    return;
  }

  // اوکی → ارور خالی
  if (errorEl) errorEl.textContent = '';

  // 🎨 پیش‌نمایش زنده
  if (preview) {
    try {
      const url = URL.createObjectURL(file);
      preview.src = url;
      preview.style.display = '';
    } catch (e) {
      // اگر مرورگر اجازه نداد، نادیده می‌گیریم
    }
  }
}

function attachFileEnhancements(scope = document) {
  scope.querySelectorAll('input[type="file"]').forEach(input => {
    // روی empty_form template ها اجرا نکن
    if (input.dataset.enhanced === '1') return;
    if (input.closest('template') || input.closest('[data-empty-fields]')) return;

    input.dataset.enhanced = '1';
    input.addEventListener('change', function () {
      handleFileInputChange(this);
    });
  });
}

// اجرای اولیه روی کل صفحه
attachFileEnhancements();


/* افزودن سطر جدید به فرم‌ست گالری */
document.addEventListener('click',function(e){
  const btn=e.target.closest('[data-add]'); if(!btn) return;
  const wrapper=btn.closest('.gallery-wrapper'); if(!wrapper) return;
  const mgmt=wrapper.querySelector('[name$="-TOTAL_FORMS"]');
  const formsBox=wrapper.querySelector('[data-forms]');
  const stash=wrapper.querySelector('[data-empty-fields]');
  const tpl=wrapper.querySelector('template[data-empty-form]');
  if(!mgmt||!formsBox||!stash||!tpl) return;

  const total=parseInt(mgmt.value||'0',10);
  const prefix=wrapper.getAttribute('data-formset-prefix')||'';

  const inputs=Array.from(stash.querySelectorAll('input,textarea,select')).map(function(el){
    const c=el.cloneNode(true);
    const n=c.getAttribute('name')||'', id=c.getAttribute('id')||'';
    if(n) c.name=n.replace(/__prefix__/g,total);
    if(id) c.id=id.replace(/__prefix__/g,total);
    if(c.tagName==='INPUT'||c.tagName==='TEXTAREA'){
      if(c.type==='checkbox'||c.type==='radio'){ c.checked=false; }
      else{ c.value=''; }
    }
    return c;
  });
  function pick(part){ return inputs.find(el=>(el.name||'').includes(part)) || document.createTextNode(''); }

  let html=tpl.innerHTML
    .replace('__IMAGE__','').replace('__ALT__','').replace('__ORDER__','').replace('__PRIMARY__','')
    .replace(/__PREFIX__/g,`${prefix}-${total}`);
  const container=document.createElement('div'); container.innerHTML=html.trim();
  const newRow=container.firstElementChild;

  const leftCol=newRow.querySelector('div:nth-child(1)');
  const rightCol=newRow.querySelector('div:nth-child(2)');

  if(rightCol) rightCol.querySelector('label+*')?.replaceWith(pick('-image'));

  const altSlot=leftCol?.querySelector('div:nth-child(1)');
  const orderSlot=leftCol?.querySelector('.row-4 > div:nth-child(1)');
  const primaryInner=leftCol?.querySelector('.row-4 > div:nth-child(2) > div');
  const deleteSlot=leftCol?.querySelector('div:nth-child(3)');

  if(altSlot) altSlot.appendChild(pick('-alt_text'));
  if(orderSlot) orderSlot.appendChild(pick('-order'));
  if(primaryInner) primaryInner.appendChild(pick('-is_primary'));
  if(deleteSlot) deleteSlot.appendChild(pick('-DELETE'));

  formsBox.appendChild(newRow);
  mgmt.value = String(total + 1);

  attachFileEnhancements(newRow);
});
/* ساخت نوار ذخیره چسبان بالا برای هر پنل */
(function(){
  document.querySelectorAll('.panel.tab-panel').forEach(function(section){
    const act = section.querySelector(':scope > .actions');
    if(!act) return;
    const topBar = act.cloneNode(true);
    topBar.classList.add('actions--top');
    section.prepend(topBar);
    act.remove();
  });
})();

/* نمایش فیلد زیرشاخه دلخواه وقتی "سایر/Other" است */
(function(){
  const subSel    = document.getElementById('id_subcategory') || document.querySelector('[name="subcategory"]');
  const customRow = document.getElementById('custom-subcat-row');

  function syncCustomRow(){
    if (!subSel || !customRow) return;
    const opt = subSel.options[subSel.selectedIndex] || null;
    const text = opt ? (opt.textContent || "").trim() : "";
    const value = (opt ? opt.value : "") || "";
    const isOther = text === "سایر" || text.toLowerCase() === "other";

    customRow.style.display = isOther ? "" : "none";
  }

  subSel && subSel.addEventListener('change', syncCustomRow);
  syncCustomRow();
})();

/* دکمه نمایش/مخفی کردن رمز عبور */
document.addEventListener("DOMContentLoaded", function() {
  document.querySelectorAll(".toggle-password").forEach(btn => {
    btn.addEventListener("click", () => {
      const input = btn.parentElement.querySelector("input");
      const icon  = btn.querySelector("i");
      if (!input) return;

      if (input.type === "password") {
        input.type = "text";
        icon.classList.remove("fa-eye");
        icon.classList.add("fa-eye-slash");
      } else {
        input.type = "password";
        icon.classList.remove("fa-eye-slash");
        icon.classList.add("fa-eye");
      }
    });
  });
});
/* ========= تب‌ها بدون رفرش + غیرفعال کردن فیلدهای تب‌های مخفی ========= */
(function(){
  const tabs   = document.querySelectorAll('.tabs a[data-tab]');
  const panels = document.querySelectorAll('.tab-panel[data-tab]');
  const hidden = document.getElementById('active_tab_input');

  if (!tabs.length || !panels.length) return;

  // همه کنترل‌های یک پنل را فعال/غیرفعال می‌کند
  function setPanelEnabled(panel, enabled) {
    panel.querySelectorAll(
      'input:not([type="hidden"]), select:not([multiple]), textarea, button'
    ).forEach(ctrl => {
      if (!ctrl.hasAttribute('data-always-enabled')) {
        ctrl.disabled = !enabled;
      }
    });
  }

  function activate(tabName, updateUrl) {
    panels.forEach(p => {
      const isActive = (p.dataset.tab === tabName);

      // نمایش/مخفی‌سازی
      p.style.display = isActive ? '' : 'none';

      // فعال/غیرفعال کردن فیلدها
      setPanelEnabled(p, isActive);
    });

    // لینک‌های تب
    tabs.forEach(a => {
      const isActive = (a.dataset.tab === tabName);
      a.setAttribute('aria-current', isActive ? 'page' : 'false');
    });

    // hidden input برای ویو
    if (hidden) hidden.value = tabName;

    // آپدیت URL بدون رفرش
    if (updateUrl) {
      const url = new URL(window.location.href);
      url.searchParams.set('tab', tabName);
      history.replaceState(null, '', url);
    }
  }

  // کلیک روی تب‌ها
  tabs.forEach(a => {
    a.addEventListener('click', function(e){
      e.preventDefault();
      const tabName = this.dataset.tab;
      if (!tabName) return;
      activate(tabName, true);
    });
  });

  // فعال‌سازی اولیه با تب فعلی از سرور
  activate('{{ active_tab }}', false);
})();


document.addEventListener("click", function(e){
    let btn = e.target.closest("[data-add]");
    if(!btn) return;

    const wrapper = btn.closest(".gallery-wrapper");
    const forms = wrapper.querySelector("[data-forms]");
    const totalInput = wrapper.querySelector(`[name$='-TOTAL_FORMS']`);

    const emptyTemplate = wrapper.querySelector("template[data-empty-form]").innerHTML;
    const emptyFields = wrapper.querySelector("[data-empty-fields]").innerHTML;

    let total = parseInt(totalInput.value, 10);

    let html = emptyTemplate
        .replace(/__PREFIX__/g, total)
        .replace("__ALT__", emptyFields.match(/name=".*-alt_text"/)[0])
        .replace("__IMAGE__", emptyFields.match(/name=".*-image"/)[0])
        .replace("__ORDER__", emptyFields.match(/name=".*-order"/)[0])
        .replace("__PRIMARY__", emptyFields.match(/name=".*-is_primary"/)[0]);

    const div = document.createElement("div");
    div.innerHTML = html;
    forms.appendChild(div);

    totalInput.value = total + 1;
});

/* ========= Theme toggle (light / dark, saved in localStorage) ========= */
(function(){
  const STORAGE_KEY = 'artonomy-theme';

  function getInitialTheme(){
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === 'dark' || saved === 'light') return saved;
    // fallback: system preference
    return window.matchMedia &&
           window.matchMedia('(prefers-color-scheme: dark)').matches
           ? 'dark'
           : 'light';
  }

  function applyTheme(theme){
    const root = document.documentElement;
    root.setAttribute('data-theme', theme);

    // label for all theme buttons
    document.querySelectorAll('.theme-toggle-btn').forEach(btn => {
      if (!btn) return;
      if (theme === 'dark'){
        btn.textContent = '☀️ حالت روشن';
      } else {
        btn.textContent = '🌙 حالت تیره';
      }
    });
  }

  const initial = getInitialTheme();
  applyTheme(initial);

  document.querySelectorAll('.theme-toggle-btn').forEach(btn => {
    btn.addEventListener('click', function(){
      const current = document.documentElement.getAttribute('data-theme') || 'light';
      const next = current === 'dark' ? 'light' : 'dark';
      applyTheme(next);
      localStorage.setItem(STORAGE_KEY, next);
    });
  });
})();
