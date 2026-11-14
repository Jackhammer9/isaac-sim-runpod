"""Exercise real Xvfb/Fluxbox/window-fit integration in the built image (no GPU)."""
import os
from pathlib import Path
import subprocess
import time
from selkies.Xlib import X, display

ROOT = Path('/opt/isaac-desktop')
WEB = Path('/opt/selkies-env/lib/python3.12/site-packages/selkies/selkies_web')
assert 'desktop-fit.js?v=2' in (WEB / 'index.html').read_text()
assert (WEB / 'desktop-fit.js').read_text() == (ROOT / 'selkies-fit.js').read_text()
assert Path(os.environ['__EGL_VENDOR_LIBRARY_FILENAMES']).is_file()
os.environ['DISPLAY'] = ':1'
children = []


def start(command):
    children.append(subprocess.Popen(command))


def eventually(check, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if check():
                return
        except Exception:
            pass
        time.sleep(.1)
    raise AssertionError('Desktop geometry did not converge')


try:
    start(['Xvfb', ':1', '-screen', '0', '1920x1080x24', '+extension', 'GLX',
           '+render', '-noreset', '-nolisten', 'tcp'])
    eventually(lambda: Path('/tmp/.X11-unix/X1').exists())
    connection = display.Display(':1')
    root = connection.screen().root
    config = Path('/root/.fluxbox')
    config.mkdir(exist_ok=True)
    (config / 'overlay').write_text('background: unset\n')
    start(['fluxbox'])
    eventually(lambda: root.get_full_property(connection.intern_atom('_NET_SUPPORTING_WM_CHECK'), X.AnyPropertyType))
    window = root.create_window(50, 50, 640, 480, 0,
                                connection.screen().root_depth, X.InputOutput, X.CopyFromParent)
    window.set_wm_name('Desktop resize integration check')
    window.set_wm_class('IsaacSim', 'Isaac Sim Full 6.2.0')
    window.map()
    connection.sync()
    eventually(lambda: window.get_full_property(connection.intern_atom('_NET_FRAME_EXTENTS'), X.AnyPropertyType))
    start(['/opt/selkies-env/bin/python3', str(ROOT / 'fit-isaac-window.py')])

    def fitted(width, height):
        g = root.get_geometry()
        if (g.width, g.height) != (width, height):
            return False
        panel_top = None
        for panel in root.query_tree().children:
            role = panel.get_full_property(connection.intern_atom('WM_WINDOW_ROLE'), X.AnyPropertyType)
            if role is not None and role.value == b'fluxbox-toolbar':
                p = panel.get_geometry()
                if p.y + p.height + 2 * p.border_width != height:
                    return False
                panel_top = p.y
        f = window.query_tree().parent.get_geometry()
        return (f.x == f.y == 0 and f.width + 2 * f.border_width == width
                and f.height + 2 * f.border_width == panel_top)

    for width, height in [(1600, 900), (1920, 1072), (1920, 944), (1920, 1072)]:
        subprocess.run(['/opt/selkies-env/bin/selkies', 'resize', f'{width}x{height}'], check=True)
        eventually(lambda: fitted(width, height))
        print(f'PASS {width}x{height}: no gap, clipping or taskbar overlap', flush=True)
finally:
    for child in reversed(children):
        child.terminate()
    for child in reversed(children):
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
