/**
 * ConnectionCanvas
 * ─────────────────────────────────────────────────────────────────
 * Draws S-curve lines between panel cards on a fixed viewport canvas.
 *
 * Usage:
 *   const cc = new ConnectionCanvas();
 *   cc.draw(selectedId, connections);   // redraw
 *   cc.clear();                         // wipe
 *   cc.destroy();                       // remove from DOM
 *
 * connections: array of { from_id, to_id } objects (from read_connections).
 * Only edges where from_id or to_id equals selectedId are drawn.
 *
 * Colors:
 *   outbound (selected → neighbour)  — accent green
 *   inbound  (neighbour → selected)  — blue
 */

class ConnectionCanvas {
  constructor() {
    const cvs = document.createElement('canvas');
    Object.assign(cvs.style, {
      position:      'fixed',
      inset:         '0',
      width:         '100vw',
      height:        '100vh',
      pointerEvents: 'none',
      zIndex:        '50',
    });
    document.body.appendChild(cvs);
    this._cvs = cvs;
    this._resize();

    this._onResize = () => { this._resize(); this._redraw(); };
    this._onScroll = () => this._redraw();
    window.addEventListener('resize', this._onResize);
    // Re-draw on scroll inside any scrollable ancestor of the panel grid
    document.querySelector('.panels-area')
      ?.addEventListener('scroll', this._onScroll, { passive: true });

    this._selectedId  = null;
    this._connections = [];
  }

  // ── Public API ────────────────────────────────────────────────────

  draw(selectedId, connections) {
    this._selectedId  = selectedId  ?? null;
    this._connections = connections ?? [];
    this._redraw();
  }

  clear() {
    this._selectedId = null;
    this._redraw();
  }

  destroy() {
    window.removeEventListener('resize', this._onResize);
    document.querySelector('.panels-area')
      ?.removeEventListener('scroll', this._onScroll);
    this._cvs.remove();
  }

  // ── Internal ──────────────────────────────────────────────────────

  _resize() {
    this._cvs.width  = window.innerWidth;
    this._cvs.height = window.innerHeight;
  }

  _redraw() {
    const ctx = this._cvs.getContext('2d');
    ctx.clearRect(0, 0, this._cvs.width, this._cvs.height);

    if (!this._selectedId) return;

    const selCard = document.querySelector(`.panel-card[data-id="${this._selectedId}"]`);
    if (!selCard) return;
    const sc = this._center(selCard);

    const ACCENT = '#00e87c';
    const BLUE   = '#3b82f6';

    for (const edge of this._connections) {
      const isOut = String(edge.from_id) === String(this._selectedId);
      const isIn  = String(edge.to_id)   === String(this._selectedId);
      if (!isOut && !isIn) continue;

      const neighbourId   = isOut ? edge.to_id : edge.from_id;
      const neighbourCard = document.querySelector(`.panel-card[data-id="${neighbourId}"]`);
      if (!neighbourCard) continue;

      const nc = this._center(neighbourCard);
      const [x1, y1, x2, y2] = isOut
        ? [sc.x, sc.y, nc.x, nc.y]
        : [nc.x, nc.y, sc.x, sc.y];

      this._curve(ctx, x1, y1, x2, y2, isOut ? ACCENT : BLUE);
    }
  }

  _center(el) {
    const r = el.getBoundingClientRect();
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
  }

  _curve(ctx, x1, y1, x2, y2, color) {
    const dx   = x2 - x1;
    const hx   = Math.max(Math.abs(dx) * 0.45, 60);
    const cx1  = x1 + hx;
    const cx2  = x2 - hx;

    ctx.save();
    ctx.strokeStyle = color;
    ctx.lineWidth   = 1.5;
    ctx.globalAlpha = 0.75;
    ctx.setLineDash([]);
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.bezierCurveTo(cx1, y1, cx2, y2, x2, y2);
    ctx.stroke();

    // Arrowhead at target
    const angle = Math.atan2(y2 - (y2 * 0.02 + y1 * 0.98), x2 - cx2);
    const len   = 7;
    ctx.beginPath();
    ctx.moveTo(x2, y2);
    ctx.lineTo(x2 - len * Math.cos(angle - 0.45), y2 - len * Math.sin(angle - 0.45));
    ctx.lineTo(x2 - len * Math.cos(angle + 0.45), y2 - len * Math.sin(angle + 0.45));
    ctx.closePath();
    ctx.fillStyle   = color;
    ctx.globalAlpha = 0.9;
    ctx.fill();
    ctx.restore();
  }
}
