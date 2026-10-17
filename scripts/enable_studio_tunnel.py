#!/usr/bin/env python3
"""One-time interactive enrollment, then launchd manages the Studio tunnel."""
import os
from pathlib import Path
import plistlib
import subprocess
import time
import urllib.request

home = Path.home()
key = home / '.ssh/macstudio_ai_tunnel'
host = 'torsteinlunde@192.168.86.33'
label = 'no.bilspillai.studio-tunnel'
plist = home / 'Library/LaunchAgents' / (label + '.plist')
entry = 'restrict,port-forwarding,permitopen="127.0.0.1:8780",command="/usr/bin/false" ' + key.with_suffix('.pub').read_text().strip()
# Public key only; the private key remains on this MacBook.
remote = '''umask 077; mkdir -p "$HOME/.ssh"; touch "$HOME/.ssh/authorized_keys"; IFS= read -r entry; grep -qxF "$entry" "$HOME/.ssh/authorized_keys" || printf '%s\\n' "$entry" >> "$HOME/.ssh/authorized_keys"'''
print('Skriv Studio-passordet når SSH spør. Det vises ikke mens du skriver.', flush=True)
subprocess.run(['/usr/bin/ssh', '-o', 'ConnectTimeout=10', host, remote], input=entry+'\n', text=True, check=True)
base = ['/usr/bin/ssh', '-N', '-T', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes', '-i', str(key), '-o', 'ExitOnForwardFailure=yes', '-o', 'ConnectTimeout=10', '-o', 'ServerAliveInterval=15', '-o', 'ServerAliveCountMax=3']
# Prove the new key works before touching the existing manual tunnel.
probe = subprocess.Popen(base + ['-L', '127.0.0.1:18780:127.0.0.1:8780', host])
try:
    for attempt in range(15):
        if probe.poll() is not None:
            raise RuntimeError('Nøkkeltesten feilet. Den eksisterende tunnelen er beholdt.')
        try:
            with urllib.request.urlopen('http://127.0.0.1:18780/networks', timeout=2) as response:
                assert response.status == 200
            break
        except OSError:
            time.sleep(1)
    else:
        raise RuntimeError('Tjenesten svarte ikke gjennom nøkkeltunnelen.')
finally:
    probe.terminate()
    probe.wait(timeout=10)

# Only retire the matching manual SSH tunnel; never kill another listener.
result = subprocess.run(['/usr/sbin/lsof', '-t', '-iTCP:8780', '-sTCP:LISTEN'], capture_output=True, text=True)
for pid in set(result.stdout.split()):
    command = subprocess.check_output(['/bin/ps', '-p', pid, '-o', 'command='], text=True).strip()
    if command.startswith('ssh -N -L 8780:127.0.0.1:8780 ') and command.endswith(host):
        os.kill(int(pid), 15)

service = f'gui/{os.getuid()}/{label}'
subprocess.run(['/bin/launchctl', 'bootout', service], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
subprocess.run(['/bin/launchctl', 'bootstrap', f'gui/{os.getuid()}', str(plist)], check=True)
for attempt in range(15):
    try:
        with urllib.request.urlopen('http://127.0.0.1:8780/networks', timeout=2) as response:
            assert response.status == 200
        print('Ferdig: automatisk tunnel er aktiv på http://127.0.0.1:8780. Du kan lukke Terminal.')
        break
    except OSError:
        time.sleep(1)
else:
    raise RuntimeError('Tunnelen er installert, men svarer ikke ennå. Se ~/Library/Logs/BilspillAI/studio-tunnel.log')
