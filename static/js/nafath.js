/**
 * نظام محاكاة النفاذ الوطني الموحد - بوابة أسواق النفع العام
 * وزارة البيئة والمياه والزراعة - منصة نما
 */

let nafathTimerInterval = null;
let currentNafathCode = null;

function getNafathUser() {
    try {
        if (localStorage.getItem('nafath_logged_out') === 'true') {
            return null;
        }
        const raw = localStorage.getItem('nafath_user');
        if (raw) return JSON.parse(raw);
        // مستخدم نفاذ افتراضي معتمد للمنصة (كما في الصورة)
        const defaultUser = {
            name: "سليمان بن عبدالله العبدالله",
            national_id: "1098234142",
            authenticated: true,
            login_time: new Date().toLocaleTimeString('ar-SA')
        };
        localStorage.setItem('nafath_user', JSON.stringify(defaultUser));
        return defaultUser;
    } catch (e) {
        return null;
    }
}

function renderNafathUI() {
    const user = getNafathUser();
    const container = document.getElementById('nafath-auth-container');
    const topGreeting = document.getElementById('top-user-greeting');
    const topName = document.getElementById('top-user-name');
    const topId = document.getElementById('top-user-id');

    if (user && user.national_id) {
        // حالة: مسجل الدخول بالنفاذ الوطني
        if (topGreeting && topName && topId) {
            topName.innerText = user.name;
            topId.innerText = user.national_id;
            topGreeting.classList.remove('hidden');
        }

        if (container) {
            container.innerHTML = `
                <div class="flex items-center gap-1.5 sm:gap-2.5 bg-slate-50 hover:bg-slate-100/90 border border-slate-200/90 py-1 sm:py-1.5 px-2 sm:px-3 rounded-xl sm:rounded-2xl shadow-xs transition shrink-0 max-w-[150px] sm:max-w-none">
                    <!-- أيقونة الهوية الوطنية الرسمية -->
                    <div class="w-8 h-8 rounded-xl bg-gradient-to-br from-[#006837] to-[#004e29] text-white flex items-center justify-center shrink-0 shadow-xs border border-emerald-500/20">
                        <i data-lucide="shield-check" class="w-4 h-4 text-naamaGold-400"></i>
                    </div>

                    <!-- بيانات المستفيد: الاسم ورقم الهوية الوطنية -->
                    <div class="text-right leading-tight min-w-0">
                        <div class="font-black text-slate-900 text-[11px] sm:text-xs truncate max-w-[80px] sm:max-w-[170px]" title="${user.name}">${user.name}</div>
                        <div class="hidden sm:block text-[10px] text-slate-500 font-bold mt-0.5">
                            الهوية: <span class="text-slate-600 font-bold tracking-wider">${user.national_id}</span>
                        </div>
                    </div>

                    <!-- فاصل عمودي ناعم -->
                    <span class="h-5 w-px bg-slate-200 inline-block mx-0.5"></span>

                    <!-- زر الخروج الأنيق -->
                    <button type="button" onclick="logoutNafath()" title="تسجيل الخروج" class="text-rose-500 hover:text-rose-700 hover:bg-rose-50 px-2 py-1 rounded-xl transition flex items-center gap-1 text-[11px] font-bold shrink-0">
                        <i data-lucide="log-out" class="w-3.5 h-3.5 text-rose-500"></i>
                        <span class="hidden sm:inline">خروج</span>
                    </button>
                </div>
            `;
        }
    } else {
        // حالة: غير مسجل الدخول
        if (topGreeting) {
            topGreeting.classList.add('hidden');
        }

        if (container) {
            container.innerHTML = `
                <button type="button" onclick="openNafathModal()" class="bg-[#006837] hover:bg-[#00542c] text-white text-xs font-black px-4 py-2.5 rounded-2xl shadow-md transition flex items-center gap-2 border border-emerald-500 hover:shadow-lg transform active:scale-95">
                    <div class="w-6 h-6 rounded-lg bg-white/15 flex items-center justify-center text-white border border-white/20">
                        <i data-lucide="fingerprint" class="w-4 h-4 text-naamaGold-400"></i>
                    </div>
                    <span>الدخول عبر النفاذ الوطني</span>
                </button>
            `;
        }
    }

    if (window.lucide) {
        lucide.createIcons();
    }
}

function ensureNafathModalInDOM() {
    if (document.getElementById('nafath-modal')) return;

    const modalDiv = document.createElement('div');
    modalDiv.id = 'nafath-modal';
    modalDiv.className = 'fixed inset-0 z-50 hidden overflow-y-auto bg-slate-900/70 backdrop-blur-sm flex items-center justify-center p-3 sm:p-5';
    modalDiv.innerHTML = `
        <div class="relative bg-white rounded-3xl shadow-2xl max-w-md w-full border border-slate-200 overflow-hidden flex flex-col animate-in fade-in zoom-in-95 duration-200">
            <!-- ترويسة نفاذ الرسمية -->
            <div class="bg-gradient-to-l from-[#00381e] via-[#00542c] to-[#006837] text-white p-6 border-b-2 border-naamaGold-500 flex items-center justify-between">
                <div class="flex items-center gap-3">
                    <div class="w-12 h-12 rounded-2xl bg-white/10 flex items-center justify-center border border-white/20 shadow-inner">
                        <i data-lucide="fingerprint" class="w-7 h-7 text-naamaGold-400"></i>
                    </div>
                    <div>
                        <div class="flex items-center gap-2">
                            <h3 class="text-base font-black text-white">النفاذ الوطني الموحد</h3>
                            <span class="bg-naamaGold-500 text-mewa-950 text-[10px] font-black px-2 py-0.5 rounded">NAFATH</span>
                        </div>
                        <p class="text-xs text-emerald-200 mt-0.5">بوابة الدخول الموحدة للخدمات الحكومية</p>
                    </div>
                </div>
                <button type="button" onclick="closeNafathModal()" class="w-8 h-8 rounded-xl bg-white/10 hover:bg-white/20 text-white flex items-center justify-center transition focus:outline-none">
                    <i data-lucide="x" class="w-5 h-5"></i>
                </button>
            </div>

            <!-- خطوة 1: إدخال رقم الهوية الوطنية -->
            <div id="nafath-step-1" class="p-6 space-y-5 text-xs">
                <div class="text-center space-y-1">
                    <h4 class="text-sm font-black text-slate-900">تسجيل الدخول للمنصة الوطنية لأسواق النفع العام</h4>
                    <p class="text-slate-500">أدخل رقم الهوية الوطنية أو الإقامة المسجلة في أبشر</p>
                </div>

                <div class="space-y-3.5">
                    <div>
                        <label class="block text-slate-700 font-bold mb-1.5">رقم بطاقة الهوية الوطنية / الإقامة *</label>
                        <div class="relative">
                            <input type="text" id="nafath-input-id" maxlength="10" value="1098234142" placeholder="10XXXXXXXX" class="w-full pr-11 pl-3 py-3 rounded-xl border border-slate-300 bg-white font-black text-sm tracking-wider text-slate-800 focus:ring-2 focus:ring-[#006837] focus:outline-none">
                            <i data-lucide="credit-card" class="w-5 h-5 text-slate-400 absolute top-3.5 right-3.5"></i>
                        </div>
                        <p class="text-[11px] text-slate-500 mt-1.5">أدخل رقم الهوية المسجل في نظام أبشر للمتابعة</p>
                    </div>
                </div>

                <div class="pt-2">
                    <button type="button" onclick="startNafathVerification()" class="w-full bg-[#006837] hover:bg-[#00542c] text-white font-black py-3 rounded-xl shadow-lg transition flex items-center justify-center gap-2 text-sm">
                        <i data-lucide="smartphone" class="w-4 h-4 text-naamaGold-400"></i>
                        <span>المتابعة عبر تطبيق نفاذ</span>
                    </button>
                </div>

                <div class="bg-emerald-50 border border-emerald-200 rounded-xl p-3 flex items-start gap-2 text-[11px] text-emerald-900 leading-relaxed">
                    <i data-lucide="info" class="w-4 h-4 text-emerald-600 shrink-0 mt-0.5"></i>
                    <span>سيصلك تنبيه فوري عبر تطبيق نفاذ المثبت على هاتفك الذكي لاختيار الرقم التأكيدي.</span>
                </div>
            </div>

            <!-- خطوة 2: شاشة انتظار التأكيد في تطبيق نفاذ الهاتف -->
            <div id="nafath-step-2" class="hidden p-6 space-y-6 text-xs text-center">
                <div class="space-y-1">
                    <h4 class="text-sm font-black text-slate-900">تأكيد الدخول عبر تطبيق نفاذ</h4>
                    <p class="text-slate-500">افتح تطبيق نفاذ على هاتفك الذكي وتأكد من اختيار الرقم الظاهر أدناه:</p>
                </div>

                <!-- الدائرة الخضراء الشهيرة لكود نفاذ -->
                <div class="flex flex-col items-center justify-center my-4">
                    <div class="relative flex items-center justify-center">
                        <div class="w-28 h-28 rounded-full bg-emerald-50 border-4 border-dashed border-[#006837] flex items-center justify-center animate-spin" style="animation-duration: 10s;"></div>
                        <div class="absolute w-24 h-24 rounded-full bg-gradient-to-tr from-[#004d26] to-[#006837] flex items-center justify-center shadow-xl text-white">
                            <span id="nafath-display-code" class="text-4xl font-black tracking-widest text-naamaGold-400">48</span>
                        </div>
                    </div>
                    <div class="mt-4 flex items-center gap-2 text-slate-500 font-bold">
                        <i data-lucide="clock" class="w-4 h-4 text-amber-600"></i>
                        <span>الوقت المتبقي للتحقق: <b id="nafath-timer" class="text-amber-600">60</b> ثانية</span>
                    </div>
                </div>

                <div class="space-y-2 pt-2">
                    <button type="button" onclick="completeNafathLogin()" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-black py-3 rounded-xl shadow-md transition flex items-center justify-center gap-2 text-xs">
                        <i data-lucide="check-check" class="w-4 h-4 text-naamaGold-400"></i>
                        <span>محاكاة قبول الطلب في تطبيق نفاذ فوراً</span>
                    </button>
                    <button type="button" onclick="resetToStep1()" class="w-full py-2 text-slate-500 hover:text-slate-800 text-xs font-bold transition">
                        إلغاء والعودة للخطوة السابقة
                    </button>
                </div>
            </div>

            <!-- خطوة 3: نجاح تسجيل الدخول -->
            <div id="nafath-step-3" class="hidden p-8 space-y-4 text-center">
                <div class="w-16 h-16 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto shadow-inner animate-bounce">
                    <i data-lucide="check" class="w-9 h-9 stroke-[3]"></i>
                </div>
                <div class="space-y-1">
                    <h4 class="text-base font-black text-slate-900">تم التحقق بنجاح من الهوية!</h4>
                    <p class="text-xs text-slate-500">تمت مطابقة الهوية الوطنية عبر النفاذ الوطني الموحد بنجاح</p>
                </div>
                <div class="bg-slate-50 border border-slate-200 p-3.5 rounded-2xl text-xs space-y-1">
                    <div class="font-black text-slate-800" id="nafath-success-name">عبدالله المنصور</div>
                    <div class="text-emerald-700 font-bold" id="nafath-success-id">هوية وطنية: 1098234142</div>
                </div>
                <div class="text-[11px] text-slate-400 font-medium">جاري تحويلك وإظهار بياناتك في المنصة...</div>
            </div>
        </div>
    `;

    document.body.appendChild(modalDiv);
    if (window.lucide) lucide.createIcons();
}

function openNafathModal() {
    ensureNafathModalInDOM();
    resetToStep1();
    const modal = document.getElementById('nafath-modal');
    modal.classList.remove('hidden');
    if (window.lucide) lucide.createIcons();
}

function closeNafathModal() {
    const modal = document.getElementById('nafath-modal');
    if (modal) modal.classList.add('hidden');
    if (nafathTimerInterval) {
        clearInterval(nafathTimerInterval);
        nafathTimerInterval = null;
    }
}

function resetToStep1() {
    if (nafathTimerInterval) {
        clearInterval(nafathTimerInterval);
        nafathTimerInterval = null;
    }
    const s1 = document.getElementById('nafath-step-1');
    const s2 = document.getElementById('nafath-step-2');
    const s3 = document.getElementById('nafath-step-3');
    if (s1) s1.classList.remove('hidden');
    if (s2) s2.classList.add('hidden');
    if (s3) s3.classList.add('hidden');
}

function startNafathVerification() {
    const idInput = document.getElementById('nafath-input-id');
    const nationalId = (idInput?.value || '').trim();

    if (!nationalId || nationalId.length < 10) {
        alert("يرجى إدخال رقم هوية وطنية أو إقامة صحيح (10 أرقام)");
        return;
    }

    // توليد رقم عشوائي بين 11 و 99 كود نفاذ
    currentNafathCode = Math.floor(Math.random() * 88) + 11;
    const displayCode = document.getElementById('nafath-display-code');
    if (displayCode) displayCode.innerText = currentNafathCode;

    document.getElementById('nafath-step-1').classList.add('hidden');
    document.getElementById('nafath-step-2').classList.remove('hidden');

    let seconds = 60;
    const timerEl = document.getElementById('nafath-timer');
    if (timerEl) timerEl.innerText = seconds;

    if (nafathTimerInterval) clearInterval(nafathTimerInterval);
    nafathTimerInterval = setInterval(() => {
        seconds--;
        if (timerEl) timerEl.innerText = seconds;
        if (seconds <= 0) {
            clearInterval(nafathTimerInterval);
            alert("انتهى وقت تأكيد نفاذ. يرجى المحاولة مرة أخرى.");
            resetToStep1();
        }
    }, 1000);

    if (window.lucide) lucide.createIcons();

    // محاكاة القبول التلقائي من التطبيق بعد ثانيتين ونصف
    setTimeout(() => {
        const step2 = document.getElementById('nafath-step-2');
        if (step2 && !step2.classList.contains('hidden')) {
            completeNafathLogin();
        }
    }, 2500);
}

function completeNafathLogin() {
    if (nafathTimerInterval) {
        clearInterval(nafathTimerInterval);
        nafathTimerInterval = null;
    }

    const idInput = document.getElementById('nafath-input-id');
    const nationalId = (idInput?.value || "1098234142").trim();

    // استرجاع الاسم الموثق بالسجل المدني تلقائياً
    const citizenName = (nationalId === "1098234142") 
        ? "سليمان بن عبدالله العبدالله" 
        : "عبدالله بن فهد المنصور";

    const userObj = {
        name: citizenName,
        national_id: nationalId,
        authenticated: true,
        login_time: new Date().toLocaleTimeString('ar-SA')
    };

    localStorage.removeItem('nafath_logged_out');
    localStorage.setItem('nafath_user', JSON.stringify(userObj));

    const s2 = document.getElementById('nafath-step-2');
    const s3 = document.getElementById('nafath-step-3');
    if (s2) s2.classList.add('hidden');
    if (s3) s3.classList.remove('hidden');

    const sName = document.getElementById('nafath-success-name');
    const sId = document.getElementById('nafath-success-id');
    if (sName) sName.innerText = userObj.name;
    if (sId) sId.innerText = `الهوية الوطنية: ${userObj.national_id}`;

    if (window.lucide) lucide.createIcons();

    setTimeout(() => {
        closeNafathModal();
        renderNafathUI();
        showNafathToast(`مرحباً بك يا ${userObj.name}، تم تسجيل دخولك بنجاح عبر النفاذ الوطني.`);
    }, 1200);
}

function logoutNafath() {
    localStorage.removeItem('nafath_user');
    localStorage.setItem('nafath_logged_out', 'true');
    renderNafathUI();
    showNafathToast("تم تسجيل الخروج من النفاذ الوطني بنجاح.");
}

function showNafathToast(message) {
    let toast = document.getElementById('nafath-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'nafath-toast';
        toast.className = 'fixed bottom-6 left-6 z-50 transform transition-all duration-300 translate-y-24 opacity-0 pointer-events-none';
        toast.innerHTML = `
            <div class="bg-[#00381e] text-white px-5 py-3.5 rounded-2xl shadow-2xl flex items-center gap-3 text-xs font-bold border border-naamaGold-500">
                <i data-lucide="check-circle" class="w-4 h-4 text-naamaGold-400"></i>
                <span id="nafath-toast-msg">${message}</span>
            </div>
        `;
        document.body.appendChild(toast);
    } else {
        const msg = document.getElementById('nafath-toast-msg');
        if (msg) msg.innerText = message;
    }

    if (window.lucide) lucide.createIcons();

    toast.classList.remove('translate-y-24', 'opacity-0');
    setTimeout(() => {
        toast.classList.add('translate-y-24', 'opacity-0');
    }, 3500);
}

// تشغيل تلقائي عند جاهزية الصفحة
document.addEventListener('DOMContentLoaded', () => {
    ensureNafathModalInDOM();
    renderNafathUI();
});
