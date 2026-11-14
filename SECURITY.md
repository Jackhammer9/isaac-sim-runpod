# Security

Use GitHub's private vulnerability reporting for security issues when available;
do not publish credentials or sensitive logs in public issues. Rotate accidentally
disclosed credentials at their provider immediately.

- SSH is the authentication boundary. Desktop ports bind to loopback only.
- Do not forward the desktop to a public interface without authentication/TLS.
- The container runs as root because desktop dependencies and the supported
  Isaac setup require it; it is not an isolation boundary for untrusted users.
- Do not enable privileged mode or mount your Docker socket into the desktop.
- Load trusted assets/extensions/scripts. Simulation content can execute code.
- Image tags identify source revisions. Prefer digests for reproducibility.
- CI publishes with the repository's short-lived GitHub token. No long-lived
  registry credentials are required in source or Docker build arguments.
- The runtime receives only your SSH public key. Keep private keys on your client.
- Dependency versions are pinned where practical; this is a community project,
  not a promise of continuous security maintenance or NVIDIA support.
