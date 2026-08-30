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