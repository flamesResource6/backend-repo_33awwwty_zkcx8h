import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Product, Video, TradeAccount, Order

app = FastAPI(title="Creator Commerce & Paper Trading API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Backend running", "endpoints": ["/api/products", "/api/videos", "/api/trading/*", "/test"]}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

# -----------------------------
# Simple product catalog
# -----------------------------
class CreateProduct(BaseModel):
    title: str
    description: Optional[str] = None
    price: float
    category: str

@app.post("/api/products")
def create_product(payload: CreateProduct):
    try:
        prod = Product(**payload.model_dump())
        prod_id = create_document("product", prod)
        return {"id": prod_id, "message": "Product created"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/products")
def list_products():
    try:
        docs = get_documents("product")
        # Convert ObjectId to string
        for d in docs:
            if d.get("_id"): d["_id"] = str(d["_id"])
        return docs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------
# Simple video list (UGC links)
# -----------------------------
class CreateVideo(BaseModel):
    title: str
    description: Optional[str] = None
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    creator: Optional[str] = None

@app.post("/api/videos")
def create_video(payload: CreateVideo):
    try:
        vid = Video(**payload.model_dump())
        vid_id = create_document("video", vid)
        return {"id": vid_id, "message": "Video added"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/videos")
def list_videos():
    try:
        docs = get_documents("video")
        for d in docs:
            if d.get("_id"): d["_id"] = str(d["_id"])
        return docs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------
# Paper trading (virtual money)
# -----------------------------
class CreateAccount(BaseModel):
    user_id: str

@app.post("/api/trading/account")
def create_account(payload: CreateAccount):
    try:
        # initialize with 10k and empty positions
        acct = TradeAccount(user_id=payload.user_id)
        acct_id = create_document("tradeaccount", acct)
        return {"id": acct_id, "message": "Account created", "cash_balance": acct.cash_balance}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class Quote(BaseModel):
    symbol: str
    price: float

# simple fake quote source (no external API): deterministic pseudo price
@app.get("/api/trading/quote")
def get_quote(symbol: str):
    s = symbol.upper()
    base = sum(ord(c) for c in s) % 200 + 20  # 20..219
    price = round(float(base) + 0.13 * (base % 7), 2)
    return {"symbol": s, "price": price}

class PlaceOrder(BaseModel):
    user_id: str
    symbol: str
    side: str
    quantity: float

@app.post("/api/trading/order")
def place_order(order: PlaceOrder):
    # get a quote
    quote = get_quote(order.symbol)
    price = quote["price"]

    # fetch or create account on the fly
    from pymongo.collection import Collection
    acct_col: Collection = db["tradeaccount"]
    acct = acct_col.find_one({"user_id": order.user_id})
    if not acct:
        acct_model = TradeAccount(user_id=order.user_id)
        acct_id = create_document("tradeaccount", acct_model)
        acct = acct_col.find_one({"_id": ObjectId(acct_id)})

    cash = float(acct.get("cash_balance", 0))
    positions: Dict[str, float] = acct.get("positions", {})

    cost = price * order.quantity
    if order.side == "buy":
        if cost > cash:
            ord_model = Order(user_id=order.user_id, symbol=order.symbol.upper(), side='buy', quantity=order.quantity, price=price, status='rejected', reason='Insufficient funds')
            create_document("order", ord_model)
            raise HTTPException(status_code=400, detail="Insufficient funds")
        cash -= cost
        positions[order.symbol.upper()] = positions.get(order.symbol.upper(), 0) + order.quantity
    elif order.side == "sell":
        if positions.get(order.symbol.upper(), 0) < order.quantity:
            ord_model = Order(user_id=order.user_id, symbol=order.symbol.upper(), side='sell', quantity=order.quantity, price=price, status='rejected', reason='Not enough shares')
            create_document("order", ord_model)
            raise HTTPException(status_code=400, detail="Not enough shares")
        cash += cost
        positions[order.symbol.upper()] = positions.get(order.symbol.upper(), 0) - order.quantity
    else:
        raise HTTPException(status_code=400, detail="Invalid side")

    # persist updates
    db["tradeaccount"].update_one({"_id": acct["_id"]}, {"$set": {"cash_balance": cash, "positions": positions}})

    ord_model = Order(user_id=order.user_id, symbol=order.symbol.upper(), side=order.side, quantity=order.quantity, price=price, status='filled')
    order_id = create_document("order", ord_model)

    return {"id": order_id, "status": "filled", "price": price, "cash_balance": cash, "positions": positions}

@app.get("/api/trading/portfolio")
def get_portfolio(user_id: str):
    acct = db["tradeaccount"].find_one({"user_id": user_id})
    if not acct:
        raise HTTPException(status_code=404, detail="Account not found")
    acct["_id"] = str(acct["_id"]) if acct.get("_id") else None
    return acct

# -----------------------------
# Schemas exposure for database UI
# -----------------------------
@app.get("/schema")
def get_schema():
    from inspect import getmembers, isclass
    import schemas as schema_module
    classes = {name: cls.model_json_schema() for name, cls in getmembers(schema_module) if isclass(cls) and hasattr(cls, 'model_json_schema')}
    return classes


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
