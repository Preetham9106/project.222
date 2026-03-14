from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "cloudkitchen123"

DB_PATH = "cloud_kitchen.db"


# ---------------- DATABASE ----------------
def init_db():

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        price REAL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT,
        quantity INTEGER,
        total REAL,
        date TEXT
    )
    """)

    # Default admin user
    cursor.execute("SELECT * FROM users WHERE username='admin'")
    admin = cursor.fetchone()

    if not admin:
        cursor.execute(
            "INSERT INTO users (username,password) VALUES (?,?)",
            ("admin","admin123")
        )

    conn.commit()
    conn.close()


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username,password)
        )

        user = cursor.fetchone()
        conn.close()

        if user:
            session["admin"] = True
            return redirect("/")
        else:
            return render_template("login.html",error="Invalid Login")

    return render_template("login.html")


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():

    session.clear()
    return redirect("/login")


# ---------------- HOME ----------------
@app.route("/")
def index():

    if not session.get("admin"):
        return redirect("/login")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM items")
    items = cursor.fetchall()

    conn.close()

    now = datetime.now()

    current_date = now.strftime("%d %B %Y")
    current_time = now.strftime("%I:%M %p")

    return render_template(
        "index.html",
        items=items,
        current_date=current_date,
        current_time=current_time
    )


# ---------------- ADD ITEM ----------------
@app.route("/add", methods=["GET","POST"])
def add_item():

    if not session.get("admin"):
        return redirect("/login")

    if request.method == "POST":

        name = request.form.get("name")
        price = request.form.get("price")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO items (name,price) VALUES (?,?)",
            (name,price)
        )

        conn.commit()
        conn.close()

        return redirect("/")

    return render_template("add_item.html")


# ---------------- EDIT PRICE ----------------
@app.route("/edit_price/<int:id>", methods=["GET","POST"])
def edit_price(id):

    if not session.get("admin"):
        return redirect("/login")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if request.method == "POST":

        price = request.form.get("price")

        cursor.execute(
            "UPDATE items SET price=? WHERE id=?",
            (price,id)
        )

        conn.commit()
        conn.close()

        return redirect("/")

    cursor.execute("SELECT * FROM items WHERE id=?",(id,))
    item = cursor.fetchone()

    conn.close()

    return render_template("edit_price.html",item=item)


# ---------------- DELETE ITEM ----------------
@app.route("/delete/<int:id>")
def delete(id):

    if not session.get("admin"):
        return redirect("/login")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM items WHERE id=?",(id,))

    conn.commit()
    conn.close()

    return redirect("/")


# ---------------- PLACE ORDER ----------------
@app.route("/order", methods=["GET","POST"])
def place_order():

    if not session.get("admin"):
        return redirect("/login")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM items")
    items = cursor.fetchall()

    if request.method == "POST":

        customer_name = request.form.get("customer_name")
        phone_number = request.form.get("phone_number")

        item_ids = request.form.getlist("item_id")
        quantities = request.form.getlist("quantity")

        total_amount = 0
        total_quantity = 0
        order_items = []

        for item_id,qty in zip(item_ids,quantities):

            if qty and int(qty) > 0:

                cursor.execute(
                    "SELECT name,price FROM items WHERE id=?",
                    (item_id,)
                )

                item = cursor.fetchone()

                if item:

                    subtotal = item[1] * int(qty)

                    total_amount += subtotal
                    total_quantity += int(qty)

                    order_items.append(f"{item[0]} x {qty}")

        if total_quantity > 0:

            date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            items_text = ", ".join(order_items)

            cursor.execute(
            "INSERT INTO orders (item_name,quantity,total,date) VALUES (?,?,?,?)",
            (items_text,total_quantity,total_amount,date)
            )

            conn.commit()

            order_id = cursor.lastrowid

            conn.close()

            return redirect(
            f"/bill/{order_id}?name={customer_name}&phone={phone_number}"
            )

    conn.close()

    return render_template("place_order.html",items=items)


# ---------------- BILL ----------------
@app.route("/bill/<int:order_id>")
def bill(order_id):

    if not session.get("admin"):
        return redirect("/login")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM orders WHERE id=?",(order_id,))
    order = cursor.fetchone()

    conn.close()

    if order:
        subtotal = order[3]
        gst = round(subtotal * 0.05,2)
        total = round(subtotal + gst,2)
    else:
        gst = 0
        total = 0

    customer_name = request.args.get("name")
    phone_number = request.args.get("phone")

    return render_template(
        "bill.html",
        order=order,
        gst=gst,
        total=total,
        kitchen_name="Cloud Kitchen",
        kitchen_address="Bangalore, India",
        customer_name=customer_name,
        phone_number=phone_number
    )


# ---------------- VIEW ORDERS ----------------
@app.route("/orders")
def view_orders():

    if not session.get("admin"):
        return redirect("/login")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM orders")
    orders = cursor.fetchall()

    conn.close()

    return render_template("orders.html",orders=orders)


# ---------------- DELETE ORDER ----------------
@app.route("/delete_order/<int:id>")
def delete_order(id):

    if not session.get("admin"):
        return redirect("/login")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM orders WHERE id=?",(id,))

    conn.commit()
    conn.close()

    return redirect("/orders")


# ---------------- RUN APP ----------------
if __name__ == "__main__":

    init_db()

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
