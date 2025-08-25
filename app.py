import os, requests
from flask import Flask, request

APP_ID = os.environ.get("APP_ID")
APP_SECRET = os.environ.get("APP_SECRET")
REDIRECT_URI = os.environ.get("REDIRECT_URI")  # بعد از دیپلوی ست می‌کنی
V = "v23.0"
FB_AUTH = f"https://www.facebook.com/{V}/dialog/oauth"
GRAPH = f"https://graph.facebook.com/{V}"

SCOPES = ",".join([
    "instagram_basic",
    "pages_show_list",
    "pages_read_engagement",
    "pages_manage_metadata",
    "instagram_manage_insights",
    "instagram_content_publish",
])

app = Flask(__name__)

@app.get("/")
def home():
    if not (APP_ID and APP_SECRET and REDIRECT_URI):
        return "<h3>Set APP_ID, APP_SECRET, REDIRECT_URI env vars first.</h3>"
    url = (
        f"{FB_AUTH}?client_id={APP_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={SCOPES}&response_type=code&state=csrf123"
    )
    return f'<a href="{url}">Login with Instagram (Meta API v23.0)</a>'

@app.get("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return f"<pre>No code. Params: {dict(request.args)}</pre>"

    # code -> user access token
    token_resp = requests.get(f"{GRAPH}/oauth/access_token", params={
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "redirect_uri": REDIRECT_URI,
        "code": code
    })
    t = token_resp.json()
    token = t.get("access_token")
    if not token:
        return f"<h3>Error getting token</h3><pre>{t}</pre>"

    me = requests.get(f"{GRAPH}/me", params={"access_token": token}).json()
    pages = requests.get(f"{GRAPH}/me/accounts", params={"access_token": token}).json()

    # resolve ig_user_id if possible
    ig_user_id, picked_page = None, None
    for p in pages.get("data", []):
        pid = p.get("id")
        if not pid: 
            continue
        r = requests.get(f"{GRAPH}/{pid}", params={
            "fields": "instagram_business_account",
            "access_token": token
        }).json()
        ig = r.get("instagram_business_account", {})
        if ig and ig.get("id"):
            ig_user_id, picked_page = ig["id"], pid
            break

    ig_info, ig_media = {}, {}
    if ig_user_id:
        ig_info = requests.get(f"{GRAPH}/{ig_user_id}", params={
            "fields": "username,media_count",
            "access_token": token
        }).json()
        ig_media = requests.get(f"{GRAPH}/{ig_user_id}/media", params={
            "fields": "id,caption,media_type,permalink,timestamp",
            "limit": 5,
            "access_token": token
        }).json()

    return f"""
    <h2>Token</h2><pre>{t}</pre>
    <h2>/me</h2><pre>{me}</pre>
    <h2>/me/accounts</h2><pre>{pages}</pre>
    <h2>Picked Page</h2><pre>{picked_page}</pre>
    <h2>IG User ID</h2><pre>{ig_user_id}</pre>
    <h2>IG Info</h2><pre>{ig_info}</pre>
    <h2>IG Media (5)</h2><pre>{ig_media}</pre>
    """

# صفحات ثابت برای App Review (ساده ولی کافی)
@app.get("/privacy")
def privacy():
    return "Privacy Policy: We store OAuth tokens securely and let users revoke access anytime."

@app.get("/data-deletion")
def data_deletion():
    return "Data Deletion: Email support@insightino.local to request deletion. We remove tokens & data within 7 days."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
