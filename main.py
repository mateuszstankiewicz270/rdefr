from flask import Flask, render_template, request, jsonify
import httpx
import re
import json

app = Flask(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " \ 
             "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"

def scrape_tiktok_profile(username):
    url = f"https://www.tiktok.com/@{username}"
    headers = {"User-Agent": USER_AGENT}
    try:
        with httpx.Client(timeout=10) as client:
            r = client.get(url, headers=headers)
            if r.status_code != 200:
                return {"error": f"Failed to load TikTok profile (status {r.status_code})"}

            m = re.search(r'<script id="SIGI_STATE" type="application/json">(.+?)</script>', r.text)
            if not m:
                return {"error": "Failed to find profile data in page"}

            data_json = m.group(1)
            data = json.loads(data_json)

            user_info = data.get("UserModule", {}).get("users", {}).get(username, {})
            stats = data.get("UserModule", {}).get("stats", {}).get(username, {})

            if not user_info:
                return {"error": "User not found or profile is private"}

            profile = {
                "nickname": user_info.get("nickname", ""),
                "uniqueId": user_info.get("uniqueId", ""),
                "signature": user_info.get("signature", ""),
                "avatar": user_info.get("avatarLarger", ""),
                "verified": user_info.get("verified", False),
                "followers": stats.get("followerCount", 0),
                "following": stats.get("followingCount", 0),
                "likes": stats.get("heartCount", 0),
                "videos": []
            }

            items = data.get("ItemList", {}).get("user-post", {}).get("list", [])
            for vid_id in items[:12]:
                video = data.get("ItemModule", {}).get(vid_id, {})
                if video:
                    profile["videos"].append({
                        "id": vid_id,
                        "desc": video.get("desc", ""),
                        "cover": video.get("video", {}).get("cover", ""),
                        "play": video.get("video", {}).get("playAddr", "")
                    })

            return profile

    except Exception as e:
        return {"error": f"Exception: {str(e)}"}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/profile")
def profile_api():
    username = request.args.get("username", "").strip().lstrip("@")
    if not username:
        return jsonify({"error": "Username parameter missing"}), 400
    result = scrape_tiktok_profile(username)
    if "error" in result:
        return jsonify({"error": result["error"]}), 404
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)