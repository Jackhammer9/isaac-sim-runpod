// Fit the primary desktop after Chrome maximizes, restores or enters fullscreen.
(() => {
  if (location.hash.startsWith('#display2')) return;
  let viewport = '';
  let input = null;
  let resetTimer = null;

  function resetAfterLayout() {
    clearTimeout(resetTimer);
    resetTimer = setTimeout(() => {
      requestAnimationFrame(() => requestAnimationFrame(() => {
        if (!window.webrtcInput || window.enable_resize === false) return;
        window.postMessage({type: 'resetResolutionToWindow'}, window.location.origin);
      }));
    }, 180);
  }

  function fit() {
    const width = window.innerWidth;
    const height = window.innerHeight;
    if (!width || !height) return;
    // Selkies measures its container. Refresh the cached height before resizing.
    document.documentElement.style.setProperty('--vh', `${height * 0.01}px`);
    const app = document.getElementById('app');
    if (app && (app.style.getPropertyValue('height') !== `${height}px` ||
                app.style.getPropertyPriority('height') !== 'important')) {
      app.style.setProperty('height', `${height}px`, 'important');
    }
    const key = `${width}x${height}:${window.devicePixelRatio || 1}`;
    if (viewport !== key || input !== window.webrtcInput) {
      viewport = key;
      input = window.webrtcInput;
      resetAfterLayout();
    }

    document.querySelectorAll('.video-container').forEach(container => {
      const canvas = container.querySelector('#videoCanvas');
      const video = [...container.querySelectorAll('video')].find(v => v.videoWidth > 0);
      const sourceWidth = video?.videoWidth || canvas?.width;
      const sourceHeight = video?.videoHeight || canvas?.height;
      if (!sourceWidth || !sourceHeight || !container.clientWidth || !container.clientHeight) return;
      const scale = Math.min(container.clientWidth / sourceWidth, container.clientHeight / sourceHeight);
      const w = sourceWidth * scale, h = sourceHeight * scale;
      const styles = {position: 'absolute', width: `${w}px`, height: `${h}px`,
        left: `${(container.clientWidth - w) / 2}px`, top: `${(container.clientHeight - h) / 2}px`,
        margin: '0px', transform: 'none', 'max-width': 'none', 'max-height': 'none'};
      container.querySelectorAll('#videoCanvas, video, #overlayInput').forEach(el => {
        for (const [name, value] of Object.entries(styles)) {
          if (el.style.getPropertyValue(name) !== value || el.style.getPropertyPriority(name) !== 'important')
            el.style.setProperty(name, value, 'important');
        }
      });
    });
  }
  window.addEventListener('resize', fit);
  window.visualViewport?.addEventListener('resize', fit);
  document.addEventListener('fullscreenchange', fit);
  setInterval(fit, 250);
  fit();
})();
