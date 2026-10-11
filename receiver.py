import hashlib
import hmac
import time

from fastapi import FastAPI, HTTPException, Request

SECRET = "demo-secret"       # the customer's copy of the signing secret
TOLERANCE_SECONDS = 300      # reject anything older than 5 minutes

app = FastAPI(title="Fake customer server")


@app.post("/hook")
async def hook(request: Request):
    body = await request.body()
    timestamp = request.headers.get("webhook-timestamp")
    signature = request.headers.get("webhook-signature", "")

    if not timestamp or not signature.startswith("sha256="):
        raise HTTPException(status_code=401, detail="missing signature")

    try:
        age = abs(time.time() - int(timestamp))
    except ValueError:
        raise HTTPException(status_code=401, detail="bad timestamp")
    if age > TOLERANCE_SECONDS:
        raise HTTPException(status_code=401, detail="timestamp too old")

    message = f"{timestamp}.".encode() + body
    expected = hmac.new(SECRET.encode(), message, hashlib.sha256).hexdigest()
    received = signature.removeprefix("sha256=")
    if not hmac.compare_digest(expected, received):
        raise HTTPException(status_code=401, detail="invalid signature")

    print("VERIFIED:", body.decode())
    return {"ok": True}