# unable to find valid certification path

## 为什么System.getProperty("javax.net.ssl.trustStore")返回 null？
System.getProperty("javax.net.ssl.trustStore") 返回 null 是完全正常的，
这并不代表 JVM 没有加载 <jave.home>/lib/security/cacerts。

在 Java 中，-Djavax.net.ssl.trustStore 是一个可选的覆盖属性：
- 默认机制： 如果启动参数中没有显式指定 -Djavax.net.ssl.trustStore=/path/to/truststore，
JVM 会默默加载默认路径（即 <java.home>/lib/security/cacerts），但不会主动向系统属性 System.getProperty("javax.net.ssl.trustStore") 中写入这个默认路径。因此直接 getProperty 拿到的是 null。
- 默认 TrustStore 顺序： JSSE 引擎在初始化时，寻找 TrustStore 的顺序如下：
1. 检查命令行或代码设置的 javax.net.ssl.trustStore。
2. 如果为 null 或文件不存在，使用默认文件 <java.home>/lib/security/jssecacerts。
3. 如果 <java.home>/lib/security/jssecacerts 不存在，使用默认文件 <java.home>/lib/security/cacerts。

确定<java.home>到底是什么：
```java 
System.out.println("实际运行使用的 JAVA_HOME: " + System.getProperty("java.home"));
// 对应的 cacerts 完整路径为: System.getProperty("java.home") + "/lib/security/cacerts"
```

> 在命令行中，-D 参数必须放在 Main 类名或 -jar 参数之前。如果放错位置，JVM 会将其作为字符串数组传递给 main(String[] args)，而不会解析为系统属性。
```java
# -D 必须紧跟 java 命令，放在 -jar 或主类之前
java -Djavax.net.ssl.trustStore=/path/to/cacerts -jar myapp.jar
```

## 开启 JVM 级别的 SSL 调试日志（最推荐）
```java
java -Djavax.net.debug=ssl:handshake:verbose -javaagent:your-agent.jar -jar your-app.jar
```
启动并触发一次 HTTPS 请求，控制台会输出详细的 TLS 握手日志。重点查找以下两部分信息：
1. 查看当前 JVM 实际加载的 TrustStore 路径： 
   在日志最上方搜索 trustStore is 或 adding as trusted certificates，
   能清晰看到 JVM 到底加载了哪个路径下的证书库。
2. 查看服务端返回的完整证书链（Server Certificate Chain）：
   搜索 Server Hello 或 Certificate chain，日志会打印出服务器下发的每一级证书信息。

## 使用 Java 代码动态打印服务端发送的证书链
编写一段测试代码，直接对目标 URL 发起 TLS 连接并打印证书链：
```java
import javax.net.ssl.*;
import java.security.cert.X509Certificate;

public class SSLCertPrinter {
    public static void main(String[] args) throws Exception {
        String host = "cowra.top"; // 替换为你的目标域名
        int port = 443;

        SSLContext sslContext = SSLContext.getInstance("TLS");
        sslContext.init(null, new TrustManager[]{
                new X509TrustManager() {
                    public void checkClientTrusted(X509Certificate[] chain, String authType) {}
                    public void checkServerTrusted(X509Certificate[] chain, String authType) {
                        System.out.println("\n========== 目标服务器返回的证书链 (共 " + chain.length + " 张) ==========");
                        for (int i = 0; i < chain.length; i++) {
                            System.out.println("【证书 " + i + "】");
                            System.out.println("Subject (使用者): " + chain[i].getSubjectDN());
                            System.out.println("Issuer  (颁发者): " + chain[i].getIssuerDN());
                            System.out.println("SerialNumber : " + chain[i].getSerialNumber().toString(16));
                            System.out.println("--------------------------------------------------");
                        }
                    }
                    public X509Certificate[] getAcceptedIssuers() { return null; }
                }
        }, new java.security.SecureRandom());

        SSLSocketFactory factory = sslContext.getSocketFactory();
        try (SSLSocket socket = (SSLSocket) factory.createSocket(host, port)) {
            socket.startHandshake();
            System.out.println("TLS 握手成功！");
        } catch (Exception e) {
            System.err.println("握手失败: " + e.getMessage());
        }
    }
}
```

输出：
```shell
========== 目标服务器返回的证书链 (共 4 张) ==========
【证书 0】
Subject (使用者): CN=cowra.top
Issuer  (颁发者): CN=YE1, O=Let's Encrypt, C=US
SerialNumber : 53716cc99e4106c7a3f05238b4f55cbda2e
--------------------------------------------------
【证书 1】
Subject (使用者): CN=YE1, O=Let's Encrypt, C=US
Issuer  (颁发者): CN=Root YE, O=ISRG, C=US
SerialNumber : 5ddd70dd31f801c85c186a7a04b80afe
--------------------------------------------------
【证书 2】
Subject (使用者): CN=Root YE, O=ISRG, C=US
Issuer  (颁发者): CN=ISRG Root X2, O=Internet Security Research Group, C=US
SerialNumber : 872165fc34b6e5fba8add5b3705fb53a
--------------------------------------------------
【证书 3】
Subject (使用者): CN=ISRG Root X2, O=Internet Security Research Group, C=US
Issuer  (颁发者): CN=ISRG Root X1, O=Internet Security Research Group, C=US
SerialNumber : 6c8f1dc727c7117f7baf853ac980f9cd
--------------------------------------------------
TLS 握手成功！
```

## 验证当前 JVM 加载了哪些证书
如果不确定 JVM 到底有没有读到你刚导入的证书，可以在调用以下几行诊断代码，直接打印出 JVM 当前实际加载的所有信任证书：
```java
import javax.net.ssl.TrustManagerFactory;
import javax.net.ssl.X509TrustManager;
import java.security.KeyStore;
import java.security.cert.X509Certificate;

public class TrustStoreChecker {
    public static void main(String[] args) throws Exception {
        TrustManagerFactory tmf = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm());
        tmf.init((KeyStore) null); // null 代表初始化默认的 TrustStore (cacerts)

        for (javax.net.ssl.TrustManager tm : tmf.getTrustManagers()) {
            if (tm instanceof X509TrustManager) {
                X509TrustManager x509tm = (X509TrustManager) tm;
                System.out.println("=== 当前 JVM 加载的信任证书总数: " + x509tm.getAcceptedIssuers().length + " ===");
                for (X509Certificate cert : x509tm.getAcceptedIssuers()) {
                    // 打印主题，看看你导入的证书 (Subject) 是否在里面
                    System.out.println("Trusted: " + cert.getSubjectDN());
                }
            }
        }
    }
}
```

## 为什么只加“根证书”仍会报 CertPathBuilderException？
即使你确实将根证书存入了 JRE 的 cacerts，以下常见原因依然会导致 Apache HttpClient 找不到证书路径：

1. 缺少中间证书（Intermediate CA）：
   - 现代 SSL 证书大多是 根证书 -> 中间证书 -> 服务器证书 三级结构。
   - 如果服务端配置不规范，在 TLS 握手中只返回了“服务器证书”，没有带上“中间证书”，而你的信任库里又只有“根证书”，Java PKIX 校验器就无法补全整个信任链（Path），从而报 unable to find valid certification path。
   - 解决办法： 将目标网站的 中间证书（Intermediate Certificate） 一并导入信任库，或者直接导入服务端证书。

2. 系统属性被改写：
   - 检查代码或 Agent 中是否有类似 System.setProperty("javax.net.ssl.trustStore", ...) 的操作。

3. Apache HttpClient 显式指定了独立的 SSLContext：
   - 在代码中，Apache HttpClient 如果被配置了自定义的 TrustStrategy 或手动加载了某个 KeyStore 文件，它就会绕过 JDK 默认的 jre/lib/security/cacerts 文件。
```java 
// 如果代码里这样写，它只会信任 custom.keystore，根本不会读 JRE 的 cacerts
SSLContext sslContext = SSLContexts.custom()
.loadTrustMaterial(new File("custom.keystore"), "password".toCharArray())
.build();
   ```

‘’’pthon
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
逐行对比两个文本文件，生成 HTML 报告。
- 按 @ 分段，高亮同行中的差异片段
- 差异片段标记"第几个@后"，鼠标悬停显示
- 单文件 HTML，无外部依赖
"""

import argparse
import html
import os
import re
from difflib import SequenceMatcher

AT = "@"


def split_fields(line):
    """按 @ 切分为若干字段，保留每段起点的 @ 位置信息。"""
    parts = line.split(AT)
    fields = []
    idx = 0
    for i, p in enumerate(parts):
        # 第 0 段前没有 @；其余段前有一个 @
        at_count = i  # 本段位于"第几个 @ 之后"，即前面已出现的 @ 数量
        start = idx
        end = idx + len(p)
        fields.append({"text": p, "at_count": at_count, "start": start, "end": end})
        idx = end + 1  # 跳过 @
    return fields


def field_index_at_offset(fields, offset):
    """给定字符偏移，返回该位置所属字段的 at_count；越界返回 None。"""
    for f in fields:
        if f["start"] <= offset <= f["end"]:
            return f["at_count"]
    return None


def lcs_opcodes(a, b):
    """返回 SequenceMatcher 的 opcodes，按 a/b 切分对齐。"""
    sm = SequenceMatcher(a=a, b=b, autojunk=False)
    return sm.get_opcodes()


def build_char_ops(a, b):
    """
    把 opcodes 转成字符级标记序列：
    '=' 相同， 'd' a 中删除， 'a' b 中新增
    """
    ops = []
    for tag, i1, i2, j1, j2 in lcs_opcodes(a, b):
        if tag == "equal":
            for _ in range(i2 - i1):
                ops.append("=")
        elif tag == "replace":
            na, nb = i2 - i1, j2 - j1
            n = max(na, nb)
            for k in range(n):
                if k < na:
                    ops.append("d")
                if k < nb:
                    ops.append("a")
        elif tag == "delete":
            for _ in range(i2 - i1):
                ops.append("d")
        elif tag == "insert":
            for _ in range(j2 - j1):
                ops.append("a")
    return ops


def group_spans(ops):
    """把连续相同 tag 的字符合并为区间 [(tag, start, end), ...]。"""
    spans = []
    if not ops:
        return spans
    cur = ops[0]
    s = 0
    for i, t in enumerate(ops):
        if t != cur:
            spans.append((cur, s, i))
            cur = t
            s = i
    spans.append((cur, s, len(ops)))
    return spans


def esc(t):
    return html.escape(t, quote=False)


def render_line(text, side, fields):
    """
    渲染一侧的行：按 @ 分段，段间插入 @ 分隔符，
    差异片段包成 <mark>，title 显示第几个@后。
    """
    if text == "":
        return '<span class="empty">（空）</span>'

    cls = "d" if side == "left" else "a"
    other_cls = "a" if side == "left" else "d"

    ops = build_char_ops(text, text)  # 单行自身，全 '='；差异在同行对照里处理
    # 其实单行无法体现差异，需要在外层按两侧对照结果高亮。
    # 改为：接收外部已经算好的"该侧高亮区间"。
    raise NotImplementedError("use render_line_diff instead")


def render_line_diff(text, side, fields, diff_ranges):
    """
    text: 本侧原始行
    side: 'left' / 'right'
    fields: split_fields 结果
    diff_ranges: [(start, end), ...] 本侧需要高亮的字符区间（按原文偏移）
    """
    if text == "":
        return '<span class="empty">（空）</span>'

    cls = "d" if side == "left" else "a"

    # 合并重叠区间
    ranges = sorted(diff_ranges)
    merged = []
    for s, e in ranges:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append([s, e])

    out = []
    cursor = 0
    for s, e in merged:
        if s > cursor:
            out.append(esc(text[cursor:s]))
        seg = text[s:e]
        # 该片段横跨的字段
        ats = set()
        for f in fields:
            if f["start"] <= s <= f["end"]:
                ats.add(f["at_count"])
            if f["start"] <= max(s, e - 1) <= f["end"]:
                ats.add(f["at_count"])
        if not ats:
            ats.add(fields[-1]["at_count"] if fields else 0)
        ats = sorted(ats)
        # 生成 title：第 N 个@后
        if len(ats) == 1:
            at = ats[0]
            title = f"位于第 {at} 个@后" if at > 0 else "位于开头（第 0 个@前）"
        else:
            title = "位于第 " + "、".join(str(a) for a in ats) + " 个@后"
        out.append(
            f'<mark class="{cls}" title="{esc(title)}">{esc(seg)}</mark>'
        )
        cursor = e
    if cursor < len(text):
        out.append(esc(text[cursor:]))

    # 再插入 @ 分隔符的可视化：保留原文 @，但给 @ 加上样式
    joined = "".join(out)
    joined = joined.replace("@", '<span class="at">@</span>')
    return joined


def diff_ranges_for_line(a, b):
    """
    计算同行 a/b 的差异区间，返回 (ranges_a, ranges_b)。
    基于 LCS 字符级 diff，将 replace/delete(左)/insert(右) 都高亮。
    """
    ops = build_char_ops(a, b)
    spans = group_spans(ops)
    ra, rb = [], []
    la = 0  # a 中已消费字符
    lb = 0  # b 中已消费字符
    for tag, s, e in spans:
        length = e - s
        if tag == "=":
            la += length
            lb += length
        elif tag == "d":
            ra.append((la, la + length))
            la += length
        elif tag == "a":
            rb.append((lb, lb + length))
            lb += length
    return ra, rb


def compare_files(left_path, right_path):
    with open(left_path, encoding="utf-8", errors="replace") as f:
        left_lines = f.read().splitlines()
    with open(right_path, encoding="utf-8", errors="replace") as f:
        right_lines = f.read().splitlines()

    n = max(len(left_lines), len(right_lines))
    rows = []
    diff_count = 0
    for i in range(n):
        a = left_lines[i] if i < len(left_lines) else ""
        b = right_lines[i] if i < len(right_lines) else ""
        fa = split_fields(a)
        fb = split_fields(b)
        if a == b:
            rows.append({"idx": i + 1, "same": True, "a": a, "b": b,
                         "fa": fa, "fb": fb, "ra": [], "rb": []})
        else:
            ra, rb = diff_ranges_for_line(a, b)
            rows.append({"idx": i + 1, "same": False, "a": a, "b": b,
                         "fa": fa, "fb": fb, "ra": ra, "rb": rb})
            diff_count += 1
    return rows, diff_count


CSS = """
* { box-sizing: border-box; }
body {
    font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif;
    margin: 0; padding: 20px 24px; background: #f5f6f8; color: #1f2328;
}
h1 { font-size: 20px; margin: 0 0 4px; }
.meta { color: #57606a; font-size: 13px; margin-bottom: 14px; }
.stats { display: flex; gap: 18px; margin-bottom: 14px; flex-wrap: wrap; }
.stat { background: #fff; border: 1px solid #d0d7de; border-radius: 8px;
    padding: 8px 14px; font-size: 13px; }
.stat b { font-size: 18px; }
.toolbar { margin-bottom: 12px; }
button { font-size: 13px; padding: 6px 12px; border: 1px solid #d0d7de;
    background: #fff; border-radius: 6px; cursor: pointer; margin-right: 8px; }
button:hover { background: #f0f3f6; }
table { width: 100%; border-collapse: collapse; background: #fff;
    border: 1px solid #d0d7de; border-radius: 8px; overflow: hidden; }
th, td { border-bottom: 1px solid #eaeef2; padding: 6px 10px;
    vertical-align: top; font-size: 13px; }
th { background: #f0f3f6; text-align: left; font-weight: 600;
    position: sticky; top: 0; z-index: 2; }
.idx { width: 56px; text-align: right; color: #57606a; user-select: none; }
.linenum { font-variant-numeric: tabular-nums; }
.side { width: 50%; font-family: "SF Mono", Consolas, "Courier New", monospace;
    word-break: break-all; line-height: 1.7; }
mark.d { background: #ffe1e1; color: #b30000; border-radius: 2px;
    padding: 0 1px; cursor: help; }
mark.a { background: #d8f5dc; color: #1a7f37; border-radius: 2px;
    padding: 0 1px; cursor: help; }
mark:hover { outline: 1px solid currentColor; }
.at { color: #8c959f; }
tr.same { display: none; }
body.show-same tr.same { display: table-row; }
tr.same .side { color: #8c959f; }
tr.diff { background: #fffdf5; }
.empty { color: #b0b8c0; font-style: italic; }
.legend { font-size: 12px; color: #57606a; margin-top: 10px; }
"""


def build_html(rows, diff_count, total, left_name, right_name):
    rows_html = []
    for r in rows:
        if r["same"]:
            cls = "same"
            rendered_a = '<span class="empty">（相同）</span>'
            rendered_b = '<span class="empty">（相同）</span>'
        else:
            cls = "diff"
            rendered_a = render_line_diff(r["a"], "left", r["fa"], r["ra"])
            rendered_b = render_line_diff(r["b"], "right", r["fb"], r["rb"])
        rows_html.append(
            f'<tr class="{cls}">'
            f'<td class="idx"><span class="linenum">{r["idx"]}</span></td>'
            f'<td class="side">{rendered_a}</td>'
            f'<td class="side">{rendered_b}</td></tr>'
        )

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>逐行对比报告</title>
<style>{CSS}</style></head><body>
<h1>逐行对比报告</h1>
<div class="meta">左侧：{esc(left_name)}　｜　右侧：{esc(right_name)}</div>
<div class="stats">
    <div class="stat">总行数 <b>{total}</b></div>
    <div class="stat">差异行 <b style="color:#b30000">{diff_count}</b></div>
    <div class="stat">相同行 <b style="color:#1a7f37">{total - diff_count}</b></div>
</div>
<div class="toolbar">
    <button onclick="document.body.classList.toggle('show-same')">切换显示相同行</button>
</div>
<table>
<thead><tr>
<th class="idx">行号</th>
<th class="side">{esc(left_name)}</th>
<th class="side">{esc(right_name)}</th>
</tr></thead>
<tbody>
{''.join(rows_html)}
</tbody></table>
<div class="legend">
    红色背景 = 左侧独有差异，绿色背景 = 右侧独有差异；鼠标悬停在差异片段上可查看其位于第几个 <b>@</b> 之后。<br>
    「第 0 个@后」表示位于行首第一个 @ 之前。
</div>
<script>
document.body.classList.remove('show-same');
</script>
</body></html>"""


def main():
    ap = argparse.ArgumentParser(description="逐行对比两个文本文件并生成 HTML 报告")
    ap.add_argument("left", help="左侧文件路径")
    ap.add_argument("right", help="右侧文件路径")
    ap.add_argument("-o", "--output", default=None, help="输出 HTML 路径")
    args = ap.parse_args()

    left_name = os.path.basename(args.left)
    right_name = os.path.basename(args.right)
    rows, diff_count = compare_files(args.left, args.right)
    total = len(rows)
    out = args.output or (os.path.splitext(left_name)[0] + "_vs_" +
                          os.path.splitext(right_name)[0] + "_diff.html")
    html_text = build_html(rows, diff_count, total, left_name, right_name)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html_text)
    print(f"总行数: {total}  差异行: {diff_count}  相同行: {total - diff_count}")
    print(f"报告已生成: {os.path.abspath(out)}")


if __name__ == "__main__":
    main()

‘’’
