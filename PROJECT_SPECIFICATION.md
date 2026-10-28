# منصة أسواق النفع العام الرقمية (Public Benefit Markets Platform)
## وثيقة التصميم المعماري والمواصفات الفنية (Architecture & Technical Specification)

---

### 1. نظرة عامة ورؤية النظام
منصة رقمية وطنية تربط أطراف سلاسل الإمداد الزراعي والغذائي في أسواق النفع العام:
- **المزارع / التاجر / مستأجر المزرعة**
- **شركات الخدمات اللوجستية والتغليف (الوسطاء)**
- **إدارة السوق والرقابة (Admin / Supervisor)**
- **المستهلك النهائي ومشتري الجملة والمباسط (Consumer / Commercial Stalls)**

---

### 2. الأدوار والمستخدمين (Roles & Permissions)

```mermaid
flowchart TD
    Admin["الإدارة والرقابة (Super Admin / Market Inspector)"]
    Merchant["التاجر / المزارع (Farmer / Producer)"]
    Broker["الوسيط اللوجستي (Logistics & Packaging Broker)"]
    Customer["المستهلك النهائي (End Consumer)"]

    Merchant -->|"1. طلب انضمام + طلبات عرض منتجات"| Admin
    Admin -->|"2. فحص واعتماد كلي/جزئي وتعديل كميات"| Merchant
    Merchant -->|"3. اختيار قناة البيع (مباشر أو وسيط)"| Broker
    Broker -->|"4. استلام، فرز، تغليف، وشحن"| Customer
    Customer -->|"5. شراء وتقييم واستلام"| Merchant
```

| الدور | الصلاحيات الرئيسية |
| :--- | :--- |
| **التاجر / المزارع** | التسجيل ورفع الوثائق الرسمية، إدراج دفعات المنتجات (Listing Requests)، اختيار قناة التنفيذ (مباشر أو عبر وسيط محدد)، إدارة المخزون، متابعة المحفظة المالية والمبيعات. |
| **إدارة السوق (Admin)** | تدقيق المنشآت والوثائق، مراجعة طلبات المنتجات (اعتماد كامل، اعتماد جزئي، تعديل الكمية المعتمدة، رفض مسبب)، إدارة نسب العمولات، تعيين وتدقيق الوسطاء اللوجستيين، مراقبة الأسعار وحركة السوق. |
| **الوسيط اللوجستي** | استلام مهام التجهيز من التجار المتعاقدين، تحديث حالة الفرز والتغليف، إصدار بوالص الشحن، متابعة تسليم الشحنات للمستهلك، وتتبع استحقاقات العمولة اللوجستية. |
| **المستهلك (Buyer)** | تصفح المنتجات المعتمدة حسب المنطقة/السوق، سلة التسوق، خيارات الدفع الإلكتروني، تتبع الطلبات لحظياً، تقييم الجودة والخدمة. |

---

### 3. مسار دورة حياة المنتج واعتماد الإدارة (Product Approval Workflow)

```mermaid
stateDiagram-v2
    [*] --> Draft: إدخال المسودة
    Draft --> PendingReview: تقديم للمراجعة
    
    state PendingReview {
        [*] --> Evaluating
        Evaluating --> FullApproval: اعتماد كامل لكل البنود
        Evaluating --> PartialApproval: اعتماد بعض البنود ورفض بعضها
        Evaluating --> QuantityAdjustment: تعديل الكميات المسموحة
        Evaluating --> Rejected: رفض الطلب مع توثيق السبب
    }

    FullApproval --> ReadyForFulfillmentMode
    PartialApproval --> ReadyForFulfillmentMode
    QuantityAdjustment --> ReadyForFulfillmentMode
    
    state ReadyForFulfillmentMode {
        [*] --> SelectChannel
        SelectChannel --> DirectSale: بيع مباشر (التاجر يغلف ويوصل)
        SelectChannel --> BrokerSale: إسناد لوسيط (فرز وتغليف وتوصيل)
    }

    DirectSale --> LiveInMarket: عرض في المتجر الحي
    BrokerSale --> LiveInMarket: عرض في المتجر الحي
    Rejected --> [*]
```

---

### 4. النموذج المالي ونظام العمولات (Financial & Commission Model)

تقوم المنصة بإجراء المقاصة الآلية فور تأكيد اكتمال الطلب والتسليم عبر المحفظة الرقمية (Escrow / Wallet Ledger):

```
[إجمالي الدفع من العميل: 100 ر.س]
          │
          ├──> في حالة البيع المباشر (Direct):
          │      ├── عمولة المنصة (مثلاً 5%): 5 ر.س
          │      └── صافي رصيد التاجر: 95 ر.س
          │
          └──> في حالة البيع عبر وسيط (Broker-assisted):
                 ├── عمولة المنصة (مثلاً 5%): 5 ر.س
                 ├── أتعاب التغليف والتوصيل للوسيط (مثلاً 10%): 10 ر.س
                 └── صافي رصيد التاجر: 85 ر.س
```

---

### 5. مخطط قاعدة البيانات المقترح (Database Schema Design)

```mermaid
erDiagram
    USERS ||--o{ STORES : owns
    STORES ||--o{ PRODUCT_LISTINGS : submits
    PRODUCT_LISTINGS ||--|{ LISTING_ITEMS : contains
    LISTING_ITEMS ||--o| PRODUCTS : becomes_active
    BROKERS ||--o{ LISTING_ITEMS : fulfills
    ORDERS ||--|{ ORDER_ITEMS : contains
    ORDER_ITEMS }|--|| PRODUCTS : references
    ORDERS ||--o{ TRANSACTIONS : settles

    USERS {
        uuid id PK
        string full_name
        string role "admin | merchant | broker | customer"
        string phone
        string email
        string status "active | pending | suspended"
    }

    STORES {
        uuid id PK
        uuid owner_id FK
        string market_name
        string commercial_reg_no
        string cr_or_freelance_doc_url
        string iban
        string region
        string status "pending | approved | rejected"
    }

    PRODUCT_LISTINGS {
        uuid id PK
        uuid store_id FK
        string submission_status "draft | submitted | reviewed | rejected"
        datetime submitted_at
        text admin_feedback
    }

    LISTING_ITEMS {
        uuid id PK
        uuid listing_id FK
        string product_name
        string category
        decimal requested_qty
        decimal approved_qty
        string unit "kg | box | bag | piece"
        decimal unit_price
        string approval_status "pending | approved | partially_approved | rejected"
        string rejection_reason
        string fulfillment_mode "direct | broker"
        uuid assigned_broker_id FK
    }

    BROKERS {
        uuid id PK
        string company_name
        decimal default_commission_rate
        string coverage_areas
        boolean is_active
    }

    ORDERS {
        uuid id PK
        uuid customer_id FK
        decimal total_amount
        decimal platform_fee
        decimal broker_fee
        decimal merchant_payout
        string payment_status "pending | paid | refunded"
        string order_status "new | packing | out_for_delivery | delivered | cancelled"
    }
```

---

### 6. المكدس التقني المقترح للتنفيذ (Recommended Tech Stack)

1. **واجهة المستخدم واللوحات (Frontend & Portals):**
   - **Next.js 14+ / React (Vite / Tailwind CSS / Lucide Icons)**
   - دعم كامل للغة العربية والاتجاه من اليمين لليسار (RTL) مع تصميم عصري وسريع.
   - 4 بوابات تفاعلية متصلة:
     - 🛍️ **متجر المستهلك (Consumer Storefront)**
     - 👨‍🌾 **لوحة التاجر والمزارع (Merchant Portal)**
     - 🛡️ **لوحة إدارة السوق والاعتمادات (Admin Governance Portal)**
     - 🚚 **لوحة الوسيط وشركات التوصيل (Broker Logistics Portal)**

2. **الواجهة الخلفية وقاعدة البيانات (Backend & API):**
   - بنية خدماتية معتمدة على REST/API أو Next.js Fullstack مع SQLite/PostgreSQL لدعم سرعة التطوير وحفظ البيانات الحية.

---

### 7. خطة العمل والتنفيذ (Roadmap to MVP)

- [x] **تحديد المواصفات المعمارية ودورة حياة الطلبات والعمولات.**
- [ ] **بناء وتجهيز النظام التفاعلي الشامل (Interactive Working Prototype / MVP).**
- [ ] **اختبار سيناريوهات الاعتماد الجزئي، تعديل الكميات، واختيار قنوات البيع (مباشر vs وسيط).**
