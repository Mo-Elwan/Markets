import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "markets.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # المستخدمين
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        role TEXT NOT NULL, -- admin, merchant, broker, customer
        phone TEXT,
        email TEXT,
        business_type TEXT -- مزارع, مستأجر مزرعة, تاجر جملة, وسيط تغليف وتوصيل
    );
    """)

    # شركات الوساطة والتوصيل
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS brokers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        rate_percentage REAL NOT NULL DEFAULT 10.0,
        coverage TEXT NOT NULL,
        services TEXT NOT NULL, -- استلام، فرز، تغليف، توصيل مبرد
        phone TEXT
    );
    """)

    # طلبات العرض المقدمة من التجار
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS product_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        merchant_name TEXT NOT NULL,
        business_record TEXT NOT NULL, -- سجل تجاري أو عمل حر
        notes TEXT,
        status TEXT DEFAULT 'pending', -- pending, reviewed, partially_approved, approved, rejected
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # بنود المنتجات داخل الطلب
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS request_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        image_url TEXT,
        requested_qty REAL NOT NULL,
        approved_qty REAL DEFAULT 0,
        unit TEXT NOT NULL, -- كجم, صندوق, كرتون, سلة
        unit_price REAL NOT NULL,
        approval_status TEXT DEFAULT 'pending', -- pending, approved, rejected
        rejection_reason TEXT,
        fulfillment_mode TEXT DEFAULT 'pending_selection', -- direct, broker, pending_selection
        assigned_broker_id INTEGER,
        stock_remaining REAL DEFAULT 0,
        FOREIGN KEY (request_id) REFERENCES product_requests(id),
        FOREIGN KEY (assigned_broker_id) REFERENCES brokers(id)
    );
    """)

    # الطلبات الصادرة من المستهلكين
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name TEXT NOT NULL,
        customer_phone TEXT NOT NULL,
        customer_address TEXT NOT NULL,
        total_amount REAL NOT NULL,
        platform_fee REAL NOT NULL,
        broker_fee REAL NOT NULL,
        merchant_net REAL NOT NULL,
        status TEXT DEFAULT 'new', -- new, packaging, out_for_delivery, delivered, cancelled
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # بنود الطلب
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_item_id INTEGER NOT NULL,
        product_name TEXT NOT NULL,
        quantity REAL NOT NULL,
        unit_price REAL NOT NULL,
        fulfillment_mode TEXT NOT NULL,
        broker_name TEXT,
        FOREIGN KEY (order_id) REFERENCES orders(id),
        FOREIGN KEY (product_item_id) REFERENCES request_items(id)
    );
    """)

    # إضافة أعمدة تتبع الشحن والنقل المبرد وتصنيف الطلب (مستهلك أم مبسط) لجدول orders
    cursor.execute("PRAGMA table_info(orders)")
    existing_cols = [c["name"] for c in cursor.fetchall()]
    for col, col_type in [
        ("driver_name", "TEXT"), 
        ("driver_phone", "TEXT"), 
        ("truck_plate", "TEXT"), 
        ("temperature", "TEXT"), 
        ("delivery_notes", "TEXT"),
        ("order_type", "TEXT DEFAULT 'consumer'"), # consumer (مستهلك) or commercial_stall (مبسط / دلال)
        ("distribution_location", "TEXT DEFAULT ''") # اسم ورقم المبسط أو منفذ التوزيع
    ]:
        if col.split()[0] not in existing_cols:
            cursor.execute(f"ALTER TABLE orders ADD COLUMN {col}")

    # إضافة أعمدة تقييد الأصناف وسقف كمية المستهلك لجدول request_items
    cursor.execute("PRAGMA table_info(request_items)")
    existing_ri_cols = [c["name"] for c in cursor.fetchall()]
    for col, col_type in [
        ("is_restricted", "INTEGER DEFAULT 0"), # 0 = غير مقيد، 1 = مقيد بسقف للمستهلك
        ("max_consumer_qty", "REAL DEFAULT 5.0") # الحد الأقصى للمستهلك (مثلاً 5 كجم أو 3 كراتين)
    ]:
        if col.split()[0] not in existing_ri_cols:
            cursor.execute(f"ALTER TABLE request_items ADD COLUMN {col}")

    # ضبط إعدادات افتراضية لبعض الأصناف الاستراتيجية كأصناف مقيدة
    cursor.execute("""
    UPDATE request_items 
    SET is_restricted = 1, max_consumer_qty = 10.0 
    WHERE (name LIKE '%طماطم%' OR name LIKE '%بطاطس%' OR name LIKE '%خيار%') AND (is_restricted IS NULL OR is_restricted = 0)
    """)
    cursor.execute("""
    UPDATE request_items 
    SET is_restricted = 1, max_consumer_qty = 2.0 
    WHERE (category = 'مواشي حية' OR name LIKE '%أغنام%' OR name LIKE '%خراف%') AND (is_restricted IS NULL OR is_restricted = 0)
    """)

    # بذر بيانات أولية للاختبار السريع إذا كان الجدول فارغاً
    cursor.execute("SELECT COUNT(*) as cnt FROM brokers")
    if cursor.fetchone()["cnt"] == 0:
        cursor.executemany("""
        INSERT INTO brokers (name, rate_percentage, coverage, services, phone)
        VALUES (?, ?, ?, ?, ?)
        """, [
            ("شركة إمداد النفع اللوجستية (وسيط أ)", 10.0, "الرياض والقصيم والخرج", "استلام من المزرعة + فرز وتغليف + شحن مبرد", "0551112233"),
            ("مؤسسة الحصاد الأخضر للتوزيع (وسيط ب)", 8.5, "المنطقة الشرقية وجدة", "تغليف كرتوني صديق للبيئة + توصيل فوري", "0554445566"),
            ("شركة طازج للخدمات الزراعية (وسيط ج)", 12.0, "المدينة المنورة ومكة وتبوك", "تخزين مبرد + وزن رقمي + توصيل خلال ساعتين", "0557778899")
        ])

    cursor.execute("SELECT COUNT(*) as cnt FROM product_requests")
    if cursor.fetchone()["cnt"] == 0:
        # 1. طلب مزرعة
        cursor.execute("""
        INSERT INTO product_requests (merchant_name, business_record, notes, status, created_at)
        VALUES ('مزرعة النخيل الذهبية (الرياض - الخرج - سوق الخضار والتمور المركزي بالخرج)', 'سجل زراعي: 1010982341', 'إنتاج محلي عالي الجودة قطفة أولى', 'pending', '2026-10-27 09:30')
        """)
        req1 = cursor.lastrowid
        cursor.executemany("""
        INSERT INTO request_items (request_id, name, category, image_url, requested_qty, approved_qty, unit, unit_price, approval_status, rejection_reason, fulfillment_mode, stock_remaining)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            (req1, "تمر خلاص الخرج الفاخر (درجة أولى)", "تمور", "https://images.unsplash.com/photo-1596704017254-9b121068fb31?w=500&auto=format&fit=crop&q=60", 600, 600, "كرتون (3 كجم)", 45.0, "pending", "", "direct", 600),
            (req1, "طماطم محمية قطاف اليوم", "خضروات", "https://images.unsplash.com/photo-1592924357228-91a4daadcfea?w=500&auto=format&fit=crop&q=60", 1200, 1200, "كجم", 3.8, "pending", "", "direct", 1200)
        ])

        # 2. طلب مربي ماشية
        cursor.execute("""
        INSERT INTO product_requests (merchant_name, business_record, notes, status, created_at)
        VALUES ('مربي ماشية معتمد - سعود الشمري (المنطقة الشرقية - حفر الباطن - سوق الماشية والأعلاف المركزي)', 'بطاقة صحية بيطرية: VET-2026-9812', 'ماشية مطعمة ومفحوصة بيطرياً', 'pending', '2026-10-27 10:15')
        """)
        req2 = cursor.lastrowid
        cursor.executemany("""
        INSERT INTO request_items (request_id, name, category, image_url, requested_qty, approved_qty, unit, unit_price, approval_status, rejection_reason, fulfillment_mode, stock_remaining)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            (req2, "أغنام نعيمي بلدي (جذعان)", "مواشي حية", "https://images.unsplash.com/photo-1516467508483-a7212febe31a?w=500&auto=format&fit=crop&q=60", 40, 40, "رأس", 1450.0, "pending", "", "broker", 40),
            (req2, "خراف نجدية أصيلة", "مواشي حية", "https://images.unsplash.com/photo-1500595046743-cd271d694d30?w=500&auto=format&fit=crop&q=60", 25, 25, "رأس", 1600.0, "pending", "", "broker", 25)
        ])

        # 3. طلب مستورد
        cursor.execute("""
        INSERT INTO product_requests (merchant_name, business_record, notes, status, created_at)
        VALUES ('مؤسسة الموانئ للاستيراد الزراعي (مكة المكرمة - جدة - سوق الخضار والفواكه المركزي بالصفا)', 'إذن استيراد: IMP-SA-2026-5541', 'بضائع مطابقة للمواصفات القياسية السعودية', 'pending', '2026-10-27 11:00')
        """)
        req3 = cursor.lastrowid
        cursor.executemany("""
        INSERT INTO request_items (request_id, name, category, image_url, requested_qty, approved_qty, unit, unit_price, approval_status, rejection_reason, fulfillment_mode, stock_remaining)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            (req3, "برتقال أبو صرة إفريقي درجة أولى", "فواكه", "https://images.unsplash.com/photo-1567306226416-28f0efdc88ce?w=500&auto=format&fit=crop&q=60", 3000, 3000, "كجم", 4.2, "pending", "", "direct", 3000)
        ])

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
