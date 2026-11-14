# Isaac Sim on Runpod

An Isaac Sim desktop in your browser, with SSH and VS Code access. Desktop
dependencies and display fixes are installed in the image, rather than downloaded
on every boot. Built around NVIDIA Isaac Sim 6.2.0 and Selkies 2.2.1.

## Quick start

1. Deploy a Secure Cloud NVIDIA RTX 4090 Pod on Runpod. This combination was
   tested with driver 595.91.07. Other GPUs/drivers have not been validated here.
2. Use a successful image tag from this repository's **Actions** / **Packages**.
   Image name: `ghcr.io/jackhammer9/isaac-sim-runpod`. Pin a full commit tag or
   digest; never assume a build succeeded because source was pushed.
3. Choose an 80 GB container disk (suggested headroom), enable SSH and expose
   **22/tcp**. Register your SSH public key in Runpod. Leave the container start
   command empty to use the image entrypoint.
4. Attach your existing network volume at `/workspace`, in the same data center
   as your GPU. Keep important files there. A container disk is temporary.
5. Start the Pod and connect using its direct SSH host/port from Runpod.

Runpod handles GPU driver access. When using local Docker, install NVIDIA
Container Toolkit and supply `--gpus all`; a CPU-only container cannot run Isaac.
Using the software is subject to NVIDIA's terms; see [LICENSE](LICENSE).

## Open the desktop

On your laptop, using the actual SSH address shown by Runpod:

```sh
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
  -L 127.0.0.1:18080:127.0.0.1:8080 \
  -L 127.0.0.1:18081:127.0.0.1:8081 \
  -p YOUR_SSH_PORT root@YOUR_SSH_HOST
```

Keep the tunnel running and open **http://127.0.0.1:18080** in Chrome.
Use **WebSockets** streaming. This setup does not require UDP, WebRTC or public
desktop ports. Fallback noVNC: http://127.0.0.1:18081/vnc.html (usually less smooth).
Selkies services are bound to loopback and have no separate desktop password:
SSH provides access control. Do not expose 8080/8081 publicly without adding
authentication and TLS. Stop unused GPU Pods in Runpod to stop compute charges.

The desktop follows browser resizing, including maximize/fullscreen. The bundled
helper keeps the Fluxbox taskbar at the bottom and Isaac above it, avoiding stale
window-manager work-area values. If an old browser preference prevents fitting,
choose **Screen settings → Reset to Window**, then reload. Browser preferences
are stored on your client; an image cannot preconfigure every browser profile.

## Launch Isaac from a terminal

Isaac starts automatically by default. After closing it, run:

```sh
issac
# Correct spelling works too:
isaac
```

Both commands work in a fresh SSH terminal without sourcing anything. They use
the packaged Isaac installation, set DISPLAY, and refuse to start a duplicate
instance. For a detached launch from SSH:

```sh
nohup issac </dev/null >>/workspace/logs/isaac-manual.log 2>&1 &
```

Set `ISAAC_AUTOSTART=0` in Runpod to start only the desktop. Set
`DESKTOP_RESOLUTION=1920x1080` to select the initial screen size; browser resizing
can change it afterward. Default stream target: H.264/NVENC, 60 FPS, 8 Mbps,
audio off. Isaac's render FPS is different from delivered browser FPS.

## VS Code Remote SSH

Install Microsoft's **Remote - SSH** extension locally. Add this to your local
SSH config, substituting the direct connection values from Runpod:

```sshconfig
Host isaac-runpod
    HostName YOUR_SSH_HOST
    User root
    Port YOUR_SSH_PORT
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    ServerAliveInterval 30
    LocalForward 127.0.0.1:18080 127.0.0.1:8080
    LocalForward 127.0.0.1:18081 127.0.0.1:8081
```

Choose **Remote-SSH: Connect to Host → isaac-runpod**, then open your project
under `/workspace`. Don't run a second tunnel on the same local ports when
VS Code already forwards them. Host/port can change after migration or restart.
Install remote extensions in the SSH window as needed. Local Codex conversations
and credentials are not automatically transferred to the Pod.

## What persists

| Location | Contents |
|---|---|
| Image, `/opt/isaac-desktop` | Desktop software, launch commands, display fixes |
| `/workspace/project` | Your repositories; clone them yourself |
| `/workspace/datasets`, `/workspace/checkpoints` | Data and model outputs |
| `/workspace/cache`, `/workspace/config` | Selected NVIDIA/Kit/user caches and application state |
| `/workspace/vscode-server` | VS Code Server installation |

Save scenes explicitly under `/workspace`. Unsaved scenes are in memory.
Other changes under `/root` or `/opt` can disappear with container replacement.
A network volume survives Pod deletion and continues billing until deleted.
Changing hosts does not transfer local disks, SSH keys or Docker's layer cache.
Personal Git credentials are intentionally not bundled or automatically restored.

## Expectations and troubleshooting

- A fresh host still downloads and unpacks the large NVIDIA image. Preinstallation
  removes runtime package installation; it does not remove image transfer time.
- First use can compile shaders and fetch remote USD assets/textures. Network
  storage caches help reuse compatible data but are not a Docker image cache.
- A heavy asset import can block the UI temporarily. Check logs and GPU memory
  before force-closing Isaac and losing an unsaved scene.
- Logs: `/workspace/logs/{isaac,selkies,fluxbox,desktop-fit}.log`.
- Black viewport: check `nvidia-smi` and `isaac.log`. GLX stays enabled; the image
  selects Mesa for EGL initialization while Isaac uses NVIDIA Vulkan. Do not
  disable GLX as a workaround.
- Desktop unreachable: check SSH/tunnel, then Selkies logs. Do not restart a Pod
  casually to fix a browser issue; save the scene before restarting.

## Build and validation

```sh
docker build --platform linux/amd64 -t isaac-sim-runpod:dev .
docker run --rm --entrypoint /opt/selkies-env/bin/python3 \
  isaac-sim-runpod:dev /opt/isaac-desktop/check-desktop.py
```

GitHub Actions builds on `main`, validates scripts and runs a real CPU
Xvfb/Fluxbox resize integration test before publishing commit-tagged images.
Tags such as `v1.0.0` also publish a versioned image. PR builds do not publish.
Large image builds need substantial free disk; the workflow frees tools on its
disposable runner and uses Docker's classic image store to avoid duplicate
containerd snapshots. Never run that runner cleanup on a development machine.

The display fixes were tested on an RTX 4090 Runpod workstation. CI's synthetic
window test verifies window/taskbar alignment at multiple sizes; it does **not**
validate Isaac rendering, simulation, all GPUs or end-to-end network latency.
A new image tag needs an actual GPU session before being described as GPU-tested.

## Security and contributions

See [SECURITY.md](SECURITY.md). No personal keys, API tokens, scenes or account
configuration belong in issues, the build context or image layers. Keep changes
small, include reproduction steps, and preserve the SSH-only desktop boundary.

## Maintainer: first publication

GitHub creates new container packages as private, even when their source
repository is public. After the first successful upload, open your GitHub
package **isaac-sim-runpod ? Package settings ? Change visibility ? Public**.
This is a separate setting from repository visibility; verify an anonymous pull
before advertising an image as public. See
[GitHub package visibility documentation](https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility).
Never make a personal workspace or a credential-containing image public.

To verify a published image without Docker credentials, use a clean client:

```sh
docker pull ghcr.io/jackhammer9/isaac-sim-runpod:COMMIT_SHA
```

When upgrading an existing Pod, save its scene, retain its existing network
volume, and remove any old container start-command override. This image uses
its packaged entrypoint; it does not need a workspace repair wrapper.
