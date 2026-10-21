# -*- coding: utf-8 -*-
"""Bilibili Evolved 国内版补丁器：把上游官方 dist 加工成能在国内直接跑的版本。

可重复执行、幂等：已经改过的地方不会重复加。

用法：
    python patch_bilibili_evolved.py <输入.user.js> <输出.user.js> [lodash路径]

补丁内容：
  1. lodash 内联（去掉 @require 外部依赖，TM 下载失败会导致整个脚本不执行）
  2. 组件 CDN：cdn.jsdelivr.net -> fastly.jsdelivr.net（路径格式一致）
  3. 备用 CDN：GitHub 源指向 flyxiu fork + ghfast 镜像
  4. 改名 Bilibili Evolved CN + 独立 @namespace（避开和官方脚本同名冲突）
  5. 版本号追加 .9（2.11.5 -> 2.11.5.9），保证永远比上一版大，TM 才会正常提示升级
  6. 更新地址、反馈渠道指向自己的 fork（LICENCE.md 要求）
"""
import os
import re
import sys

OWNER = "flyxiu"
REPO = "Bilibili-Evolved"
NAME = "Bilibili Evolved CN"
NAMESPACE = "https://github.com/%s/%s" % (OWNER, REPO)
FASTLY = "fastly.jsdelivr.net"
GHFAST = "ghfast.top/https://raw.githubusercontent.com"
MARK = b"lodash 4.17.21 inlined"

DEFAULT_LODASH = r"D:\dev\Hermes-Workspace\Home\tmp\lodash-npmmirror.js"


def patch(raw: bytes, lodash: bytes) -> bytes:
    txt = raw.decode("utf-8")

    # ---------- 1. @name / @namespace（只在第一次加 namespace）----------
    if not re.search(r"//\s*@name\s+" + re.escape(NAME), txt):
        txt = re.sub(r"//\s*@name\s+Bilibili Evolved[^\r\n]*",
                     "// @name            " + NAME + "\r\n"
                     "// @namespace       " + NAMESPACE, txt, count=1)

    # ---------- 2. @version 追加 .1 ----------
    m = re.search(r"//\s*@version\s+([\d.]+)", txt)
    if m:
        ver = m.group(1)
        if not ver.endswith(".9"):
            txt = txt.replace(m.group(0), "// @version         " + ver + ".9", 1)

    # ---------- 3. 删除 lodash 的 @require ----------
    txt = re.sub(r"//\s*@require\s+https?://[^\r\n]*lodash[^\r\n]*\r?\n", "", txt)

    # ---------- 4. CDN 换镜像 ----------
    txt = txt.replace("cdn.jsdelivr.net", FASTLY)
    # GitHub 备用源：owner -> 自己，host -> ghfast 前缀
    txt = txt.replace('c="the1812",s="raw.githubusercontent.com"',
                      'c="%s",s="%s"' % (OWNER, GHFAST))
    txt = txt.replace('const r="the1812",a={jsDelivr:',
                      'const r="%s",a={jsDelivr:' % OWNER)
    txt = txt.replace(
        "GitHub:(e,t)=>`https://raw.githubusercontent.com/${t||r}/Bilibili-Evolved/${e}/`",
        "GitHub:(e,t)=>`https://%s/${t||r}/Bilibili-Evolved/${e}/`" % GHFAST)

    # ---------- 5. 更新地址 / 反馈渠道 ----------
    txt = txt.replace(
        "https://raw.githubusercontent.com/the1812/Bilibili-Evolved/master/dist/bilibili-evolved.user.js",
        "https://%s/%s/%s/master/dist/bilibili-evolved.user.js" % (GHFAST, OWNER, REPO))
    txt = txt.replace("github.com/the1812/Bilibili-Evolved/issues/new",
                      "github.com/%s/%s/issues/new" % (OWNER, REPO))
    txt = txt.replace('href:"https://github.com/the1812/Bilibili-Evolved"',
                      'href:"https://github.com/%s/%s"' % (OWNER, REPO))
    txt = txt.replace('href:"https://github.com/the1812/Bilibili-Evolved/releases"',
                      'href:"https://github.com/%s/%s/releases"' % (OWNER, REPO))

    raw = txt.encode("utf-8")

    # ---------- 6. lodash 内联（幂等）----------
    if MARK not in raw:
        head_end = raw.find(b"// ==/UserScript==")
        if head_end < 0:
            raise RuntimeError("找不到 UserScript 头结束标记，文件格式不对")
        insert_at = raw.find(b"\n", head_end) + 1
        inject = (b"\n/* ==== lodash 4.17.21 inlined (sha256 a9705dfc...) ==== */\n"
                  + lodash + b"\n/* ==== end lodash ==== */\n")
        raw = raw[:insert_at] + inject + raw[insert_at:]

    return raw


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    src, dst = sys.argv[1], sys.argv[2]
    lodash_path = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_LODASH
    lodash = open(lodash_path, "rb").read()
    raw = open(src, "rb").read()
    out = patch(raw, lodash)
    open(dst, "wb").write(out)

    info = re.search(rb"// @version\s+(\S+)", out)
    print("输入 %d 字节 -> 输出 %d 字节" % (len(raw), len(out)))
    print("版本:", info.group(1).decode() if info else "?")
    print("已写入:", os.path.abspath(dst))


if __name__ == "__main__":
    main()
