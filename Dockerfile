# Install the desktop at build time, as root, rather than on every Pod boot.
FROM nvcr.io/nvidia/isaac-sim:6.2.0
USER root
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server tini xvfb fluxbox x11-utils x11vnc novnc websockify \
    python3-venv libxkbcommon0 libxkbcommon-x11-0 libgbm1 libgl1 libegl-mesa0 \
    ca-certificates curl git procps iproute2 \
    && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /opt/selkies-env \
    && /opt/selkies-env/bin/pip install --no-cache-dir 'selkies==2.2.1'
COPY entrypoint.py launch-isaac.sh fit-isaac-window.py \
    apply-selkies-fit.py selkies-fit.js check-desktop.py /opt/isaac-desktop/
RUN chmod +x /opt/isaac-desktop/launch-isaac.sh \
    && ln -s /opt/isaac-desktop/launch-isaac.sh /usr/local/bin/isaac \
    && ln -s /opt/isaac-desktop/launch-isaac.sh /usr/local/bin/issac \
    && /opt/selkies-env/bin/python3 /opt/isaac-desktop/apply-selkies-fit.py
ENV DISPLAY=:1 NVIDIA_DRIVER_CAPABILITIES=all \
    OMNI_KIT_ACCEPT_EULA=YES ACCEPT_EULA=Y \
    XDG_CACHE_HOME=/workspace/cache/user HF_HOME=/workspace/cache/huggingface \
    CUDA_CACHE_PATH=/workspace/cache/cuda ISAAC_AUTOSTART=1 \
    __EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/50_mesa.json
WORKDIR /workspace
EXPOSE 22
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/bin/python3", "/opt/isaac-desktop/entrypoint.py"]
