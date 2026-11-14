"""Supervise SSH, X11 and streaming; keep mutable state on the network volume."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

# Xvfb and Kit can crash while probing the host's NVIDIA GBM EGL platform.
# Mesa handles the X11/EGL setup; Isaac still selects the NVIDIA Vulkan GPU.
os.environ.setdefault('__EGL_VENDOR_LIBRARY_FILENAMES',
                      '/usr/share/glvnd/egl_vendor.d/50_mesa.json')

workspace = Path('/workspace')
logs = workspace / 'logs'
logs.mkdir(parents=True, exist_ok=True)
for name in ('project', 'datasets', 'checkpoints', 'cache/user', 'cache/cuda',
             'cache/huggingface', 'cache/kit-6.2', 'config', 'vscode-server'):
    (workspace / name).mkdir(parents=True, exist_ok=True)

# Version-specific Kit state avoids sharing incompatible shader caches.
for dest, source in (
    ('/root/.cache', workspace / 'cache/user'),
    ('/root/.nvidia-omniverse', workspace / 'config/nvidia-omniverse'),
    ('/root/.local/share/ov', workspace / 'config/ov'),
    ('/root/.vscode-server', workspace / 'vscode-server'),
    ('/isaac-sim/kit/cache', workspace / 'cache/kit-6.2'),
):
    source.mkdir(parents=True, exist_ok=True)
    path = Path(dest)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Existing image content is retained alongside the link, not deleted.
    if path.is_symlink():
        if path.resolve() == source.resolve():
            continue
        raise RuntimeError(f'Unexpected existing symlink: {path}')
    if path.exists():
        backup = path.with_name(path.name + '.image-default')
        if backup.exists():
            raise RuntimeError(f'Cannot preserve existing directory: {path}')
        path.rename(backup)
    path.symlink_to(source, target_is_directory=True)

keys = os.environ.get('PUBLIC_KEY', os.environ.get('SSH_PUBLIC_KEY', '')).strip()
if not keys:
    raise RuntimeError('No PUBLIC_KEY: enable Runpod SSH and register your public key.')
ssh_dir = Path('/root/.ssh')
ssh_dir.mkdir(mode=0o700, exist_ok=True)
ssh_dir.chmod(0o700)
(ssh_dir / 'authorized_keys').write_text(keys + '\n')
(ssh_dir / 'authorized_keys').chmod(0o600)
Path('/run/sshd').mkdir(exist_ok=True)
subprocess.run(['ssh-keygen', '-A'], check=True)

children = []
handles = []
def start(name, command, required=True):
    handle = (logs / f'{name}.log').open('a', buffering=1)
    process = subprocess.Popen(command, stdout=handle, stderr=subprocess.STDOUT,
                               stdin=subprocess.DEVNULL, start_new_session=True)
    children.append((name, process, required))
    handles.append(handle)
    print(f'{name}: started PID {process.pid}', flush=True)
    return process

stopping = False
def stop(*_):
    global stopping
    stopping = True
signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)
status = 0
try:
    start('sshd', ['/usr/sbin/sshd', '-D', '-e', '-o', 'PasswordAuthentication=no',
                   '-o', 'KbdInteractiveAuthentication=no', '-o', 'PermitRootLogin=prohibit-password'])
    start('xvfb', ['Xvfb', ':1', '-screen', '0', os.environ.get('DESKTOP_RESOLUTION', '1280x720') + 'x24',
                   '+extension', 'GLX', '+render', '-noreset', '-nolisten', 'tcp'])
    for _ in range(100):
        if subprocess.run(['xdpyinfo', '-display', ':1'], stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL).returncode == 0:
            break
        time.sleep(0.2)
    else:
        raise RuntimeError('Xvfb failed: see /workspace/logs/xvfb.log')
    fluxbox_config = Path('/root/.fluxbox')
    fluxbox_config.mkdir(exist_ok=True)
    overlay = fluxbox_config / 'overlay'
    if not overlay.exists():
        overlay.write_text('background: unset\n')
    start('fluxbox', ['fluxbox'])
    start('desktop-fit', ['/opt/selkies-env/bin/python3',
                          '/opt/isaac-desktop/fit-isaac-window.py'])
    start('selkies', ['/opt/selkies-env/bin/selkies', '--addr=127.0.0.1', '--port=8080',
          '--mode=websockets', '--enable-dual-mode=false', '--enable-https=false',
          '--enable-basic-auth=false', '--encoder=h264enc', '--framerate=60',
          '--video-bitrate=8000', '--audio-enabled=false', '--enable-resize=true',
          '--second-screen=false', '--backpressure-queue-size=4'])
    start('x11vnc', ['x11vnc', '-display', ':1', '-forever', '-shared', '-nopw',
                    '-localhost', '-rfbport', '5900', '-noxdamage'])
    start('novnc', ['websockify', '--web=/usr/share/novnc', '127.0.0.1:8081', '127.0.0.1:5900'])
    if os.environ.get('ISAAC_AUTOSTART', '1') == '1':
        start('isaac', ['/opt/isaac-desktop/launch-isaac.sh'], required=False)
    print('Desktop services started. Use SSH forwarding for 8080 (Selkies) or 8081 (noVNC).', flush=True)
    reported = set()
    while not stopping:
        for name, process, required in children:
            code = process.poll()
            if code is not None and name not in reported:
                print(f'{name}: exited {code}; see /workspace/logs/{name}.log', flush=True)
                reported.add(name)
                if required:
                    status = 1
                    stopping = True
        time.sleep(1)
finally:
    for _, process, _ in reversed(children):
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
    deadline = time.monotonic() + 15
    for _, process, _ in children:
        try:
            process.wait(timeout=max(0.1, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
    for handle in handles:
        handle.close()
sys.exit(status)
