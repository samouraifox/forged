# CVE-2022-22965 Spring4Shell — JFrog Technical Analysis

**Source URL:** https://jfrog.com/blog/springshell-zero-day-vulnerability-all-you-need-to-know/
**CVE:** CVE-2022-22965
**Fetched:** 2026-05-18
**Source type:** blog

---

## Vulnerability Overview

CVE-2022-22965, nicknamed "SpringShell" or "Spring4Shell," is a critical remote code execution flaw in Spring Framework disclosed March 31, 2022. The issue stems from Spring's data binding mechanism, which converts request parameters into Java objects—a process that became exploitable in Java 9+ environments.

## Root Cause: ClassLoader Bypass

The vulnerability exploits Java 9's new `class.getModule()` API to circumvent Spring's existing protections. Normally, Spring blocks assignments to internal attributes like `Class`, `ClassLoader`, and `ProtectionDomain`. However, this new API creates a pathway to modify `ClassLoader` properties directly.

The vulnerable data binding annotation signatures include:
```
@RequestMapping, @GetMapping, @PostMapping, @PutMapping, @DeleteMapping, @PatchMapping
```

A susceptible controller pattern would be:
```java
@GetMapping("/greeting")
public String greetingSubmit(@ModelAttribute Greeting greeting, Model model)
```

## Exploitation Mechanism

The original proof-of-concept employed a two-stage Tomcat-specific attack:

**Stage 1:** Modified `ClassLoader` attributes targeting Apache Tomcat's `AccessLogValve`, redirecting log output to the web root directory with a JSP payload pattern.

**Stage 2:** Accessed the deployed webshell via HTTP request to execute shell commands.

The webshell executed arbitrary commands passed via query parameters through Java's `Runtime.getRuntime().exec()`.

## Exploitation Requirements

Vulnerability exploitability requires:
- Spring Framework (or Spring Boot) application
- JDK 9 or later
- Request handlers using data binding with non-simple type parameters
- Request parameters mapped to Plain Old Java Objects (POJOs)

The original PoC specifically required Apache Tomcat deployment as a WAR file, but researchers anticipated broader exploitation vectors.

## Affected and Fixed Versions

**Fixed versions:**
- Spring Framework 5.2.20 or 5.3.18+
- Spring Boot 2.6.6+

**Maven upgrade example:**
```xml
<properties>
    <spring-framework.version>5.3.18</spring-framework.version>
</properties>
```

## Mitigation Without Upgrade

Spring recommended adding a `@ControllerAdvice` with disallowed field patterns:
```java
String[] denylist = new String[]{"class.*", "Class.*", "*.class.*", "*.Class.*"};
dataBinder.setDisallowedFields(denylist);
```

Spring noted this workaround remains "not fail-safe," making full upgrades preferable.

## Key Technical Distinctions

Clarifications from security researchers:
- Not a deserialization vulnerability
- Exploitable across all HTTP methods, not just GET/POST
- Affects multiple application servers beyond Tomcat
- Requires `spring-web` package (not merely `spring-beans`)

The vulnerability's impact reaches beyond the original PoC's constraints, warranting comprehensive patching regardless of deployment configuration.

## Additional Context from Spring.io Advisory

The exploit specifically targets WAR deployments on Tomcat; Spring Boot executable JARs are not vulnerable.

Vulnerable Tomcat versions: 10.0.19, 9.0.61, 8.5.77 and earlier.

Payara and Glassfish also confirmed vulnerable.

Controller method parameters annotated with `@ModelAttribute` or lacking other Spring Web annotations are vulnerable, but `@RequestBody` parameters are not directly affected.

Workaround: implement field binding restrictions via `WebDataBinder.setDisallowedFields()` with patterns: `["class.*", "Class.*", "*.class.*", "*.Class.*"]`
