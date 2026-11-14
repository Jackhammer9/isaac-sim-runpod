"""Fit Isaac to the current X11 work area after a streamed desktop resize.

Fluxbox can retain the original screen size for maximization after RandR changes.
Use EWMH requests, preserving the scene and all desktop services. Only adjust on
screen/work-area changes or when a new Isaac window appears.
"""
import time
from selkies.Xlib import X, display, protocol


def main():
    while True:
        try:
            connection = display.Display(':1')
            break
        except Exception:
            time.sleep(1)
    root = connection.screen().root
    previous = {}
    while True:
        geometry = root.get_geometry()
        panel_top = geometry.height
        # Its toolbar can remain at the previous screen's bottom even after a
        # Fluxbox reconfigure. Identify only that panel by its explicit X11 role.
        for panel in root.query_tree().children:
            role = panel.get_full_property(connection.intern_atom('WM_WINDOW_ROLE'), X.AnyPropertyType)
            if role is None or role.value != b'fluxbox-toolbar':
                continue
            bounds = panel.get_geometry()
            border = bounds.border_width
            target = (0, geometry.height - bounds.height - 2 * border,
                      geometry.width - 2 * border)
            if (bounds.x, bounds.y, bounds.width) != target:
                panel.configure(x=target[0], y=target[1], width=target[2])
                connection.sync()
            if panel.get_attributes().map_state == X.IsViewable:
                panel_top = min(panel_top, target[1])
        # _NET_WORKAREA is also stale after some RandR changes. Derive both
        # window and panel bounds from this same live screen instead.
        x, y, width, height = 0, 0, geometry.width, panel_top
        clients = root.get_full_property(connection.intern_atom('_NET_CLIENT_LIST'), X.AnyPropertyType)
        current = {}
        for window_id in clients.value if clients else []:
            window = connection.create_resource_object('window', int(window_id))
            try:
                if ((window.get_wm_class() or ('',))[0] != 'IsaacSim'
                        or window.get_wm_transient_for() is not None):
                    continue
                frame = window.get_full_property(connection.intern_atom('_NET_FRAME_EXTENTS'), X.AnyPropertyType)
                left, right, top, bottom = list(frame.value) if frame else [0, 0, 22, 3]
                key = (x, y, width, height, left, right, top, bottom)
                if previous.get(int(window_id)) == key:
                    current[int(window_id)] = key
                    continue
                def send(name, values):
                    root.send_event(protocol.event.ClientMessage(window=window,
                        client_type=connection.intern_atom(name), data=(32, values)),
                        event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
                send('_NET_WM_STATE', [0, connection.intern_atom('_NET_WM_STATE_MAXIMIZED_HORZ'),
                     connection.intern_atom('_NET_WM_STATE_MAXIMIZED_VERT'), 2, 0])
                connection.sync()
                send('_NET_MOVERESIZE_WINDOW', [1 | (15 << 8) | (2 << 12), x, y,
                     max(1, width - left - right), max(1, height - top - bottom)])
                connection.sync()
                current[int(window_id)] = key
                print(f'Fitted Isaac {int(window_id)} to {width}x{height} work area', flush=True)
            except Exception as error:
                print(f'Window changed during resize: {error}', flush=True)
        previous = current
        time.sleep(0.5)


if __name__ == '__main__':
    main()
