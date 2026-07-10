(function () {
  const config = window.FDE_DEMO_README || {};
  const homeHref = config.homeHref || "../../index.html";

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function ensureStyle() {
    if (document.getElementById("fdeDemoHelperStyle")) return;
    const style = document.createElement("style");
    style.id = "fdeDemoHelperStyle";
    style.textContent = `
      .fde-demo-nav {
        position: fixed;
        right: 18px;
        bottom: 18px;
        z-index: 80;
        display: flex;
        gap: 8px;
        align-items: center;
      }
      .fde-demo-nav a,
      .fde-demo-nav button {
        min-height: 36px;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        background: rgba(255, 255, 255, 0.96);
        color: #1f2937;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12);
        padding: 8px 11px;
        text-decoration: none;
        font: inherit;
        font-size: 13px;
        font-weight: 760;
        cursor: pointer;
      }
      .fde-demo-nav a:first-child {
        border-color: #93c5fd;
        background: #eff6ff;
        color: #1d4ed8;
      }
      .fde-demo-modal {
        position: fixed;
        inset: 0;
        z-index: 90;
        display: none;
        align-items: center;
        justify-content: center;
        padding: 24px;
        background: rgba(15, 23, 42, 0.48);
        backdrop-filter: blur(4px);
      }
      .fde-demo-modal.open {
        display: flex;
      }
      .fde-demo-modal-panel {
        width: min(1120px, calc(100vw - 32px));
        max-height: min(84vh, 820px);
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        background: #ffffff;
        box-shadow: 0 24px 70px rgba(15, 23, 42, 0.28);
        overflow: hidden;
        display: flex;
        flex-direction: column;
      }
      .fde-demo-readme-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        padding: 14px 16px;
        border-bottom: 1px solid #e2e8f0;
        background: #f8fafc;
      }
      .fde-demo-readme-title {
        display: flex;
        flex-direction: column;
        gap: 3px;
      }
      .fde-demo-readme-head strong {
        color: #172033;
        font-size: 15px;
      }
      .fde-demo-readme-head span {
        color: #64748b;
        font-size: 12px;
        font-weight: 650;
      }
      .fde-demo-modal-close {
        width: 32px;
        height: 32px;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        background: #ffffff;
        color: #334155;
        cursor: pointer;
        font-size: 20px;
        line-height: 1;
      }
      .fde-demo-readme-body {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 12px;
        padding: 14px;
        overflow: auto;
      }
      .fde-demo-readme-card {
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        background: #ffffff;
        padding: 12px;
      }
      .fde-demo-readme-card h3 {
        margin: 0 0 8px;
        color: #172033;
        font-size: 14px;
      }
      .fde-demo-readme-card p {
        margin: 0;
        color: #475569;
        font-size: 13px;
        line-height: 1.65;
      }
      .fde-demo-readme-card ol,
      .fde-demo-readme-card ul {
        margin: 0;
        padding-left: 18px;
        color: #475569;
        font-size: 13px;
        line-height: 1.65;
      }
      .fde-demo-readme-card li + li {
        margin-top: 6px;
      }
      .fde-demo-readme-card.wide {
        grid-column: span 2;
      }
      .fde-demo-readme-card.full {
        grid-column: 1 / -1;
      }
      @media (max-width: 900px) {
        .fde-demo-nav {
          left: 12px;
          right: 12px;
          bottom: 12px;
          justify-content: flex-end;
        }
        .fde-demo-modal {
          padding: 12px;
        }
        .fde-demo-modal-panel {
          width: calc(100vw - 24px);
          max-height: calc(100vh - 24px);
        }
        .fde-demo-readme-body {
          grid-template-columns: 1fr;
        }
        .fde-demo-readme-card.wide {
          grid-column: auto;
        }
      }
    `;
    document.head.appendChild(style);
  }

  function list(items, ordered) {
    const tag = ordered ? "ol" : "ul";
    return `<${tag}>${(items || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</${tag}>`;
  }

  function setModalOpen(open) {
    const modal = document.getElementById("fdeDemoReadmeModal");
    if (!modal) return;
    modal.classList.toggle("open", open);
    modal.setAttribute("aria-hidden", open ? "false" : "true");
    document.body.style.overflow = open ? "hidden" : "";
  }

  function appendReadmeModal() {
    if (!config.title || document.getElementById("fdeDemoReadmeModal")) return;
    const modal = document.createElement("div");
    modal.className = "fde-demo-modal";
    modal.id = "fdeDemoReadmeModal";
    modal.setAttribute("aria-hidden", "true");
    modal.innerHTML = `
      <div class="fde-demo-modal-panel" role="dialog" aria-modal="true" aria-labelledby="fdeDemoReadmeTitle">
        <div class="fde-demo-readme-head">
          <div class="fde-demo-readme-title">
            <strong id="fdeDemoReadmeTitle">${escapeHtml(config.title)}</strong>
            <span>${escapeHtml(config.badge || "演示脚本")}</span>
          </div>
          <button type="button" class="fde-demo-modal-close" data-fde-close aria-label="关闭演示说明">×</button>
        </div>
        <div class="fde-demo-readme-body">
          <div class="fde-demo-readme-card">
            <h3>场景演示</h3>
            <p>${escapeHtml(config.scene || "")}</p>
          </div>
          <div class="fde-demo-readme-card">
            <h3>页面分区</h3>
            ${list(config.sections || [], false)}
          </div>
          <div class="fde-demo-readme-card">
            <h3>最佳演示路径</h3>
            ${list(config.path || [], true)}
          </div>
          <div class="fde-demo-readme-card wide">
            <h3>故事线</h3>
            ${list(config.storyline || [], true)}
          </div>
          <div class="fde-demo-readme-card wide">
            <h3>数据切换与结果变化</h3>
            ${list(config.switches || [], false)}
          </div>
          <div class="fde-demo-readme-card">
            <h3>讲解重点</h3>
            ${list(config.talkTrack || [], false)}
          </div>
          <div class="fde-demo-readme-card full">
            <h3>边界说明</h3>
            <p>${escapeHtml(config.boundary || "本页面使用脱敏模拟数据，仅用于售前演示和内部共创，不替代真实业务审批、投资建议、合规结论或生产系统结果。")}</p>
          </div>
        </div>
      </div>
    `;
    modal.addEventListener("click", (event) => {
      if (event.target === modal || event.target.closest("[data-fde-close]")) {
        setModalOpen(false);
      }
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") setModalOpen(false);
    });
    document.body.appendChild(modal);
  }

  function appendNav() {
    if (document.getElementById("fdeDemoNav")) return;
    const nav = document.createElement("div");
    nav.className = "fde-demo-nav";
    nav.id = "fdeDemoNav";
    nav.innerHTML = `
      <a href="${escapeHtml(homeHref)}">返回工作台</a>
      <button type="button" data-fde-readme>演示说明</button>
    `;
    nav.querySelector("[data-fde-readme]").addEventListener("click", () => {
      setModalOpen(true);
    });
    document.body.appendChild(nav);
  }

  function init() {
    ensureStyle();
    appendReadmeModal();
    appendNav();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
