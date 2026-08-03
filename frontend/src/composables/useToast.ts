/** 轻量全局 Toast */
let toastEl: HTMLDivElement | null = null;

function ensureContainer(): HTMLDivElement {
  if (!toastEl) {
    toastEl = document.createElement('div');
    toastEl.style.cssText = `
      position: fixed; top: 16px; left: 50%; transform: translateX(-50%);
      z-index: 9999; display: flex; flex-direction: column; gap: 8px; align-items: center;
      pointer-events: none;
    `;
    document.body.appendChild(toastEl);
  }
  return toastEl;
}

export function toast(message: string, type: 'success' | 'error' = 'success') {
  const container = ensureContainer();
  const el = document.createElement('div');
  const bg = type === 'error' ? '#f44336' : '#333';
  el.textContent = message;
  el.style.cssText = `
    background: ${bg}; color: #fff; padding: 10px 20px; border-radius: 20px;
    font-size: 14px; box-shadow: 0 2px 8px rgba(0,0,0,0.2); opacity: 0;
    transition: opacity 0.25s; max-width: 80vw;
  `;
  container.appendChild(el);
  requestAnimationFrame(() => { el.style.opacity = '1'; });
  setTimeout(() => {
    el.style.opacity = '0';
    setTimeout(() => el.remove(), 250);
  }, 2000);
}
