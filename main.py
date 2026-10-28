from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
import os
from database import init_db, get_connection

init_db()

app = FastAPI(title="منصة أسواق النفع العام الوطنية", version="1.0.0")

# دعم خدمة الملفات الثابتة (الصور والخطوط والشعارات)
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === نماذج البيانات (Pydantic Models) ===

class ProductItemInput(BaseModel):
    name: str
    category: str
    description: Optional[str] = ""
    image_url: Optional[str] = "https://images.unsplash.com/photo-1540420773420-3366772f4999?w=500&auto=format&fit=crop&q=60"
    requested_qty: float
    unit: str
    unit_price: float

class CreateListingRequest(BaseModel):
    merchant_name: str
    business_record: str
    notes: Optional[str] = ""
    items: List[ProductItemInput]

class AdminReviewItem(BaseModel):
    item_id: int
    approval_status: str # approved, rejected
    approved_qty: float
    rejection_reason: Optional[str] = ""

class AdminReviewSubmission(BaseModel):
    request_id: int
    reviews: List[AdminReviewItem]

class FulfillmentSelection(BaseModel):
    item_id: int
    fulfillment_mode: str # direct, broker
    assigned_broker_id: Optional[int] = None

class CartItem(BaseModel):
    product_item_id: int
    quantity: float

class CheckoutRequest(BaseModel):
    customer_name: str
    customer_phone: str
    customer_address: str
    order_type: Optional[str] = "consumer" # consumer, commercial_stall
    distribution_location: Optional[str] = "" # اسم ورقم المبسط أو منفذ التوزيع
    items: List[CartItem]

class UpdateRestrictionRequest(BaseModel):
    item_id: int
    is_restricted: int
    max_consumer_qty: float


# === واجهات الـ API ===

@app.get("/api/brokers")
def list_brokers():
    conn = get_connection()
    brokers = conn.execute("SELECT * FROM brokers").fetchall()
    conn.close()
    return [dict(b) for b in brokers]

@app.post("/api/merchant/submit-listing")
def submit_listing(data: CreateListingRequest):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO product_requests (merchant_name, business_record, notes, status)
    VALUES (?, ?, ?, 'pending')
    """, (data.merchant_name, data.business_record, data.notes))
    req_id = cursor.lastrowid

    for item in data.items:
        cursor.execute("""
        INSERT INTO request_items (request_id, name, category, description, image_url, requested_qty, approved_qty, unit, unit_price, approval_status, stock_remaining)
        VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, 'pending', 0)
        """, (req_id, item.name, item.category, item.description or "", item.image_url, item.requested_qty, item.unit, item.unit_price))

    conn.commit()
    conn.close()
    return {"status": "success", "request_id": req_id, "message": "تم تقديم طلب عرض المنتجات بنجاح وفي انتظار مراجعة الإدارة"}

@app.get("/api/merchant/my-requests")
def get_merchant_requests(merchant_name: Optional[str] = None):
    conn = get_connection()
    query = "SELECT * FROM product_requests ORDER BY id DESC"
    requests = conn.execute(query).fetchall()
    result = []
    for r in requests:
        r_dict = dict(r)
        items = conn.execute("""
            SELECT ri.*, b.name as broker_name, b.rate_percentage as broker_rate
            FROM request_items ri
            LEFT JOIN brokers b ON ri.assigned_broker_id = b.id
            WHERE ri.request_id = ?
        """, (r["id"],)).fetchall()
        r_dict["items"] = [dict(i) for i in items]
        result.append(r_dict)
    conn.close()
    return result

@app.post("/api/merchant/set-fulfillment")
def set_fulfillment(data: FulfillmentSelection):
    conn = get_connection()
    cursor = conn.cursor()
    item = cursor.execute("SELECT * FROM request_items WHERE id = ?", (data.item_id,)).fetchone()
    if not item:
        conn.close()
        raise HTTPException(status_code=404, detail="البند غير موجود")
    if item["approval_status"] != "approved":
        conn.close()
        raise HTTPException(status_code=400, detail="لا يمكن اختيار آلية البيع لمنتج غير معتمد")

    cursor.execute("""
    UPDATE request_items
    SET fulfillment_mode = ?, assigned_broker_id = ?, stock_remaining = approved_qty
    WHERE id = ?
    """, (data.fulfillment_mode, data.assigned_broker_id if data.fulfillment_mode == 'broker' else None, data.item_id))

    conn.commit()
    conn.close()
    return {"status": "success", "message": "تم تحديث آلية البيع وأصبح المنتج متاحاً في المتجر"}

@app.get("/api/admin/requests")
def admin_get_requests():
    conn = get_connection()
    requests = conn.execute("SELECT * FROM product_requests ORDER BY id DESC").fetchall()
    result = []
    for r in requests:
        r_dict = dict(r)
        items = conn.execute("SELECT * FROM request_items WHERE request_id = ?", (r["id"],)).fetchall()
        r_dict["items"] = [dict(i) for i in items]
        result.append(r_dict)
    conn.close()
    return result

@app.post("/api/admin/review-items")
def admin_review_items(data: AdminReviewSubmission):
    conn = get_connection()
    cursor = conn.cursor()

    approved_any = False
    rejected_any = False

    for item in data.reviews:
        if item.approval_status == 'approved':
            approved_any = True
            cursor.execute("""
            UPDATE request_items 
            SET approval_status = 'approved', approved_qty = ?, rejection_reason = '', stock_remaining = ?
            WHERE id = ?
            """, (item.approved_qty, item.approved_qty, item.item_id))
        else:
            rejected_any = True
            cursor.execute("""
            UPDATE request_items 
            SET approval_status = 'rejected', approved_qty = 0, rejection_reason = ?, stock_remaining = 0
            WHERE id = ?
            """, (item.rejection_reason or "مخالفة اشتراطات السوق", item.item_id))

    overall_status = "partially_approved" if (approved_any and rejected_any) else ("approved" if approved_any else "rejected")
    cursor.execute("UPDATE product_requests SET status = ? WHERE id = ?", (overall_status, data.request_id))

    conn.commit()
    conn.close()
    return {"status": "success", "message": "تم حفظ مراجعة الإدارة وتحديث البنود"}

@app.get("/api/store/products")
def get_store_products():
    conn = get_connection()
    # المنتجات المعتمدة والتي تم تحديد آلية البيع لها ومتبقي منها مخزون
    query = """
    SELECT ri.*, pr.merchant_name, b.name as broker_name, b.rate_percentage as broker_rate
    FROM request_items ri
    JOIN product_requests pr ON ri.request_id = pr.id
    LEFT JOIN brokers b ON ri.assigned_broker_id = b.id
    WHERE ri.approval_status = 'approved' 
      AND ri.fulfillment_mode IN ('direct', 'broker')
      AND ri.stock_remaining > 0
    ORDER BY ri.id DESC
    """
    items = conn.execute(query).fetchall()
    conn.close()
    return [dict(i) for i in items]

@app.post("/api/store/checkout")
def checkout(order_data: CheckoutRequest):
    if not order_data.items:
        raise HTTPException(status_code=400, detail="السلة فارغة")

    conn = get_connection()
    cursor = conn.cursor()

    total_amount = 0.0
    platform_fee = 0.0
    broker_fee = 0.0
    merchant_net = 0.0

    items_to_process = []

    # التحقق من المخزون والأسعار وحساب العمولات
    for cart_item in order_data.items:
        row = cursor.execute("""
        SELECT ri.*, b.name as broker_name, b.rate_percentage as broker_rate
        FROM request_items ri
        LEFT JOIN brokers b ON ri.assigned_broker_id = b.id
        WHERE ri.id = ?
        """, (cart_item.product_item_id,)).fetchone()

        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail=f"المنتج رقم {cart_item.product_item_id} غير متوفر")

        if row["stock_remaining"] < cart_item.quantity:
            conn.close()
            raise HTTPException(status_code=400, detail=f"الكمية المطلوبة للمنتج ({row['name']}) غير متوفرة. المتاح: {row['stock_remaining']} {row['unit']}")

        item_total = row["unit_price"] * cart_item.quantity
        item_platform_fee = item_total * 0.05 # 5% رسوم تشغيلية للمنصة

        if row["fulfillment_mode"] == "broker":
            broker_rate = (row["broker_rate"] or 10.0) / 100.0
            item_broker_fee = item_total * broker_rate
        else:
            item_broker_fee = 0.0

        item_merchant_net = item_total - item_platform_fee - item_broker_fee

        total_amount += item_total
        platform_fee += item_platform_fee
        broker_fee += item_broker_fee
        merchant_net += item_merchant_net

        items_to_process.append({
            "item_id": row["id"],
            "name": row["name"],
            "qty": cart_item.quantity,
            "unit_price": row["unit_price"],
            "fulfillment_mode": row["fulfillment_mode"],
            "broker_name": row["broker_name"],
            "is_restricted": row["is_restricted"] if "is_restricted" in row.keys() else 0,
            "max_consumer_qty": row["max_consumer_qty"] if "max_consumer_qty" in row.keys() else 5.0,
            "new_stock": row["stock_remaining"] - cart_item.quantity
        })

    # التحقق من سقف المستهلك للأصناف المقيدة
    has_exceeded_restricted = any(
        it.get("is_restricted", 0) == 1 and it["qty"] > it.get("max_consumer_qty", 5.0)
        for it in items_to_process
    )

    final_order_type = "commercial_stall" if (has_exceeded_restricted or order_data.order_type == "commercial_stall") else "consumer"
    final_dist_loc = (order_data.distribution_location or "").strip()

    if final_order_type == "commercial_stall" and not final_dist_loc:
        conn.close()
        raise HTTPException(
            status_code=400, 
            detail="الكمية المطلوبة تتجاوز الحد الأقصى للمستهلك للأصناف المقيدة. يلزم تحديد اسم ورقم المبسط أو منفذ التوزيع بالسوق."
        )

    # تسجيل الطلب
    cursor.execute("""
    INSERT INTO orders (customer_name, customer_phone, customer_address, order_type, distribution_location, total_amount, platform_fee, broker_fee, merchant_net, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')
    """, (order_data.customer_name, order_data.customer_phone, order_data.customer_address, final_order_type, final_dist_loc, total_amount, platform_fee, broker_fee, merchant_net))
    order_id = cursor.lastrowid

    # تسجيل بنود الطلب وتحديث المخزون
    for it in items_to_process:
        cursor.execute("""
        INSERT INTO order_items (order_id, product_item_id, product_name, quantity, unit_price, fulfillment_mode, broker_name)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (order_id, it["item_id"], it["name"], it["qty"], it["unit_price"], it["fulfillment_mode"], it["broker_name"]))

        cursor.execute("UPDATE request_items SET stock_remaining = ? WHERE id = ?", (it["new_stock"], it["item_id"]))

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "order_id": order_id,
        "order_type": final_order_type,
        "distribution_location": final_dist_loc,
        "total_amount": round(total_amount, 2),
        "platform_fee": round(platform_fee, 2),
        "broker_fee": round(broker_fee, 2),
        "merchant_net": round(merchant_net, 2),
        "message": "تم تأكيد طلبك بنجاح وحجز المخزون واحتساب الرسوم التشغيلية المعتمدة"
    }

@app.get("/api/orders")
def get_orders():
    conn = get_connection()
    orders = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    res = []
    for o in orders:
        o_dict = dict(o)
        items = conn.execute("SELECT * FROM order_items WHERE order_id = ?", (o["id"],)).fetchall()
        o_dict["items"] = [dict(i) for i in items]
        res.append(o_dict)
    conn.close()
    return res

@app.get("/api/admin/restricted-settings")
def get_restricted_settings():
    conn = get_connection()
    query = """
    SELECT ri.id, ri.name, ri.category, ri.image_url, ri.requested_qty, ri.approved_qty, 
           ri.unit, ri.unit_price, ri.approval_status, ri.fulfillment_mode, ri.stock_remaining,
           COALESCE(ri.is_restricted, 0) as is_restricted, 
           COALESCE(ri.max_consumer_qty, 5.0) as max_consumer_qty, 
           pr.merchant_name
    FROM request_items ri
    JOIN product_requests pr ON ri.request_id = pr.id
    ORDER BY ri.is_restricted DESC, ri.id DESC
    """
    items = conn.execute(query).fetchall()
    
    # إحصائيات التوزيع بين الأفراد والمباسط
    consumer_orders = conn.execute("SELECT COUNT(*) as c FROM orders WHERE order_type = 'consumer'").fetchone()["c"]
    stall_orders = conn.execute("SELECT COUNT(*) as c FROM orders WHERE order_type = 'commercial_stall'").fetchone()["c"]
    recent_stall_distributions = conn.execute("""
        SELECT id, customer_name, customer_phone, distribution_location, total_amount, created_at, status
        FROM orders 
        WHERE order_type = 'commercial_stall' 
        ORDER BY id DESC LIMIT 10
    """).fetchall()
    conn.close()
    
    return {
        "items": [dict(i) for i in items],
        "stats": {
            "consumer_orders": consumer_orders,
            "stall_orders": stall_orders,
            "total_orders": consumer_orders + stall_orders
        },
        "recent_stall_distributions": [dict(d) for d in recent_stall_distributions]
    }

@app.post("/api/admin/update-restriction")
def update_product_restriction(data: UpdateRestrictionRequest):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE request_items 
    SET is_restricted = ?, max_consumer_qty = ?
    WHERE id = ?
    """, (data.is_restricted, data.max_consumer_qty, data.item_id))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "تم تحديث قيود الصنف وسقف المستهلك بنجاح"}
    return res

class OrderStatusUpdate(BaseModel):
    status: Optional[str] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    truck_plate: Optional[str] = None
    temperature: Optional[str] = None
    delivery_notes: Optional[str] = None

@app.post("/api/orders/{order_id}/status")
def update_order_status(order_id: int, status: Optional[str] = None, data: Optional[OrderStatusUpdate] = None):
    conn = get_connection()
    new_status = (data.status if data and data.status else status) or "packaging"
    driver_name = data.driver_name if data else None
    driver_phone = data.driver_phone if data else None
    truck_plate = data.truck_plate if data else None
    temperature = data.temperature if data else None
    delivery_notes = data.delivery_notes if data else None

    conn.execute("""
    UPDATE orders 
    SET status = ?,
        driver_name = COALESCE(?, driver_name),
        driver_phone = COALESCE(?, driver_phone),
        truck_plate = COALESCE(?, truck_plate),
        temperature = COALESCE(?, temperature),
        delivery_notes = COALESCE(?, delivery_notes)
    WHERE id = ?
    """, (new_status, driver_name, driver_phone, truck_plate, temperature, delivery_notes, order_id))
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"تم تحديث حالة الطلب إلى {new_status}"}

@app.get("/api/analytics")
def get_analytics():
    conn = get_connection()
    total_sales = conn.execute("SELECT COALESCE(SUM(total_amount), 0) as s FROM orders").fetchone()["s"]
    platform_earnings = conn.execute("SELECT COALESCE(SUM(platform_fee), 0) as s FROM orders").fetchone()["s"]
    broker_earnings = conn.execute("SELECT COALESCE(SUM(broker_fee), 0) as s FROM orders").fetchone()["s"]
    merchant_earnings = conn.execute("SELECT COALESCE(SUM(merchant_net), 0) as s FROM orders").fetchone()["s"]
    orders_count = conn.execute("SELECT COUNT(*) as c FROM orders").fetchone()["c"]
    products_count = conn.execute("SELECT COUNT(*) as c FROM request_items WHERE approval_status = 'approved'").fetchone()["c"]
    pending_approvals = conn.execute("SELECT COUNT(*) as c FROM product_requests WHERE status = 'pending'").fetchone()["c"]
    conn.close()

    return {
        "total_sales": round(total_sales, 2),
        "platform_earnings": round(platform_earnings, 2),
        "broker_earnings": round(broker_earnings, 2),
        "merchant_earnings": round(merchant_earnings, 2),
        "orders_count": orders_count,
        "approved_products": products_count,
        "pending_approvals": pending_approvals
    }


# === واجهات العرض والصفحات المستقلة (Dedicated HTML Pages) ===

@app.get("/", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
def index_page():
    html_file = os.path.join(os.path.dirname(__file__), "index.html")
    with open(html_file, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/submit", response_class=HTMLResponse)
@app.get("/merchant", response_class=HTMLResponse)
@app.get("/submit_request.html", response_class=HTMLResponse)
@app.get("/merchant_submit.html", response_class=HTMLResponse)
def submit_request_page():
    html_file = os.path.join(os.path.dirname(__file__), "merchant_submit.html")
    with open(html_file, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/tracking", response_class=HTMLResponse)
@app.get("/merchant_tracking.html", response_class=HTMLResponse)
def tracking_page():
    html_file = os.path.join(os.path.dirname(__file__), "merchant_tracking.html")
    with open(html_file, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/review", response_class=HTMLResponse)
@app.get("/admin", response_class=HTMLResponse)
@app.get("/review_requests.html", response_class=HTMLResponse)
def review_requests_page():
    html_file = os.path.join(os.path.dirname(__file__), "review_requests.html")
    with open(html_file, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/store", response_class=HTMLResponse)
@app.get("/store.html", response_class=HTMLResponse)
def store_page():
    html_file = os.path.join(os.path.dirname(__file__), "store.html")
    with open(html_file, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/my_orders", response_class=HTMLResponse)
@app.get("/my_orders.html", response_class=HTMLResponse)
@app.get("/orders_view", response_class=HTMLResponse)
def my_orders_page():
    html_file = os.path.join(os.path.dirname(__file__), "my_orders.html")
    with open(html_file, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/service_center_orders", response_class=HTMLResponse)
@app.get("/service_center_orders.html", response_class=HTMLResponse)
@app.get("/merchant_orders", response_class=HTMLResponse)
@app.get("/merchant_orders.html", response_class=HTMLResponse)
@app.get("/fulfillment", response_class=HTMLResponse)
def service_center_orders_page():
    html_file = os.path.join(os.path.dirname(__file__), "service_center_orders.html")
    with open(html_file, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/mobile_app", response_class=HTMLResponse)
@app.get("/mobile_app.html", response_class=HTMLResponse)
@app.get("/mobile", response_class=HTMLResponse)
@app.get("/app", response_class=HTMLResponse)
def mobile_app_page():
    html_file = os.path.join(os.path.dirname(__file__), "mobile_app.html")
    with open(html_file, "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
