from fastapi import FastAPI, Request

app = FastAPI(title="Fake customer server")


@app.post("/hook")
async def hook(request: Request):
    body = await request.body()
    print("RECEIVED BODY:", body.decode())
    print("RECEIVED HEADERS:", dict(request.headers))
    return {"ok": True}