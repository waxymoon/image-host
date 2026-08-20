#!/data/data/com.termux/files/usr/bin/python
# -*- coding: utf-8 -*-
"""
Termux 手机版：视频 -> mp3 -> 图床(GitHub) 一键脚本
用法:
  第一次:  python convert_termux.py 设置   （粘贴 GitHub token，只输一次）
  之后:    python convert_termux.py 视频文件1 [视频文件2 ...]
          支持通配符:  python convert_termux.py storage/downloads/*.mp4
"""
import sys, os, json, base64, random, subprocess, urllib.request, urllib.error

REPO = "yshuya530-svg/image-host"
BRANCH = "main"
TOKEN_FILE = os.path.expanduser("~/.gh_token")
RAW_BASE = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/"

def get_token():
    if os.path.exists(TOKEN_FILE):
        tok = open(TOKEN_FILE).read().strip()
        if tok:
            return tok
    tok = input("请粘贴 GitHub token（电脑 PicGo 配置里复制，发微信到手机再粘）：").strip()
    with open(TOKEN_FILE, "w") as f:
        f.write(tok)
    try:
        os.chmod(TOKEN_FILE, 0o600)
    except Exception:
        pass
    print("token 已保存，下次不用再输")
    return tok

def convert(src, out):
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
           "-i", src, "-vn", "-codec:a", "libmp3lame", "-b:a", "192k", out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg 转换失败: {r.stderr[-300:]}")

def upload(token, path):
    name = str(random.randint(10000000, 99999999)) + ".mp3"
    url = f"https://api.github.com/repos/{REPO}/contents/{name}"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    body = json.dumps({"message": f"upload {name}", "content": b64}).encode("utf-8")
    for _ in range(5):
        req = urllib.request.Request(url, data=body, method="PUT")
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                if r.status in (200, 201):
                    return RAW_BASE + name
        except urllib.error.HTTPError as e:
            if e.code == 409:  # 撞名，换一个
                name = str(random.randint(10000000, 99999999)) + ".mp3"
                url = f"https://api.github.com/repos/{REPO}/contents/{name}"
                body = json.dumps({"message": f"upload {name}", "content": b64}).encode("utf-8")
                continue
            if e.code == 403:
                raise RuntimeError("上传被拒(403)，token 可能过期")
            raise RuntimeError(f"上传失败 HTTP {e.code}")
    raise RuntimeError("撞名重试失败，请重试")

def main():
    if len(sys.argv) < 2:
        print("用法: python convert_termux.py 视频文件1 [视频文件2 ...]")
        print("示例: python convert_termux.py storage/downloads/*.mp4")
        print("说明: mp3 直接拖进来会上传，其他格式自动转 mp3")
        return 1

    if sys.argv[1] == "设置":
        get_token()
        print("完成！")
        return 0

    files = [a for a in sys.argv[1:] if os.path.isfile(a)]
    if not files:
        print("没找到有效的文件，检查路径对不对")
        return 1

    token = get_token()
    links = []
    for f in files:
        base = os.path.basename(f)
        print(f"▶ {base}")
        try:
            if base.lower().endswith(".mp3"):
                src = f
                print("  是 mp3，直接上传...")
            else:
                src = f + ".tmp.mp3"
                print("  转码中...")
                convert(f, src)
                print(f"  转码完成 ({os.path.getsize(src)//1024} KB)")
            link = upload(token, src)
            links.append(link)
            print(f"  ✅ {link}")
        except Exception as e:
            print(f"  ❌ {e}")
        finally:
            tmp = f + ".tmp.mp3"
            if os.path.exists(tmp):
                os.remove(tmp)
        print("")

    print("=" * 40)
    print("全部完成！链接已打印在上方，长按终端文字即可复制")
    if len(links) > 1:
        print("\n（多文件：可逐个长按复制）")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n已取消")
