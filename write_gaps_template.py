"""Write the gaps.html template to disk."""
import os

template_path = os.path.join("app", "templates", "audit", "gaps.html")

content = r"""{% extends "base.html" %}
{% block title %}Gap Checklist — Audit #{{ audit.id }} — {{ branding.company_name }}{% endblock %}
{% block content %}
<style>
  .gaps-page{max-width:960px;margin:0 auto;padding:1rem;font-family:'Barlow',sans-serif;color:#fff}
  .gaps-page h2{font-family:'Barlow Condensed',sans-serif;color:#f97316;margin-bottom:.5rem;font-size:1.6rem}
  .summary-bar{display:flex;flex-wrap:wrap;gap:.75rem;margin-bottom:1.25rem}
  .summary-card{background:#16213e;border-radius:6px;padding:.6rem 1rem;text-align:center;min-width:100px;flex:1;border:1px solid transparent;transition:all .15s;cursor:pointer;text-decoration:none}
  .summary-card .count{font-family:'Barlow Condensed',sans-serif;font-size:1.5rem;font-weight:700;color:#f97316}
  .summary-card .label{font-size:.8rem;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em}
  .summary-card:hover{background:#1e293b;border:1px solid #f97316;transform:translateY(-1px)}
  .filter-bar{display:flex;flex-wrap:wrap;gap:.75rem;margin-bottom:1.25rem;align-items:center}
  .filter-bar label{font-size:.85rem;color:#94a3b8}
  .filter-bar select{background:#1e293b;border:1px solid #334155;border-radius:4px;color:#e2e8f0;padding:.4rem .6rem;font-family:'Barlow',sans-serif;font-size:.9rem}
  .filter-bar select:focus{outline:none;border-color:#f97316}
  .filter-bar .filter-btn{background:#f97316;color:#fff;border:none;border-radius:4px;padding:.4rem 1rem;cursor:pointer;font-weight:600;font-family:'Barlow',sans-serif}
  .filter-bar .filter-btn:hover{background:#fb923c}
  .filter-bar .clear-btn{background:transparent;color:#94a3b8;border:1px solid #334155;border-radius:4px;padding:.4rem .75rem;cursor:pointer;font-family:'Barlow',sans-serif;text-decoration:none;font-size:.9rem}
  .filter-bar .clear-btn:hover{color:#fff;border-color:#f97316}
  .gap-card{background:#0f172a;border:1px solid #334155;border-radius:6px;padding:1rem;margin-bottom:1rem}
  .gap-header{display:flex;align-items:center;gap:.75rem;flex-wrap:wrap;margin-bottom:.75rem}
  .gap-code{font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:1.1rem;color:#e2e8f0}
  .gap-title{color:#cbd5e1;font-size:.95rem}
  .gap-score{font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:.95rem;padding:.15rem .5rem;border-radius:4px;background:#1e293b;color:#94a3b8}
  .badge{display:inline-block;padding:.15rem .5rem;border-radius:4px;font-size:.8rem;font-weight:600;text-transform:uppercase;letter-spacing:.03em}
  .badge-critical{background:rgba(239,68,68,.2);color:#f87171;border:1px solid rgba(239,68,68,.3)}
  .badge-high{background:rgba(249,115,22,.2);color:#fb923c;border:1px solid rgba(249,115,22,.3)}
  .badge-medium{background:rgba(250,204,21,.2);color:#fbbf24;border:1px solid rgba(250,204,21,.3)}
  .actions-section{margin-top:.5rem}
  .actions-section h4{font-family:'Barlow Condensed',sans-serif;color:#94a3b8;font-size:.9rem;margin:0 0 .4rem;text-transform:uppercase;letter-spacing:.05em}
  .action-item{background:#16213e;border-radius:4px;margin-bottom:.4rem;border:1px solid #1e293b;overflow:hidden}
  .action-summary{display:flex;flex-wrap:wrap;align-items:center;gap:.5rem;padding:.5rem .75rem;cursor:pointer;user-select:none}
  .action-summary:hover{background:#1e293b}
  .action-expand-icon{color:#64748b;font-size:.75rem;transition:transform .2s;min-width:16px}
  .action-item.expanded .action-expand-icon{transform:rotate(90deg)}
  .action-desc{flex:1;color:#e2e8f0;font-size:.9rem;min-width:150px}
  .action-meta{color:#94a3b8;font-size:.8rem}
  .action-status{padding:.1rem .4rem;border-radius:3px;font-size:.8rem;font-weight:600}
  .status-open{background:rgba(59,130,246,.2);color:#60a5fa}
  .status-in_progress{background:rgba(250,204,21,.2);color:#fbbf24}
  .status-completed{background:rgba(74,222,128,.2);color:#4ade80}
  .status-overdue{background:rgba(239,68,68,.2);color:#f87171}
  .action-detail{display:none;padding:.75rem;border-top:1px solid #334155;background:#0f172a}
  .action-item.expanded .action-detail{display:block}
  .detail-grid{display:grid;grid-template-columns:1fr 1fr;gap:.5rem;margin-bottom:.75rem}
  .detail-field label{display:block;font-size:.8rem;color:#94a3b8;margin-bottom:.2rem}
  .detail-field select,.detail-field input{background:#1e293b;border:1px solid #334155;border-radius:4px;color:#e2e8f0;padding:.35rem .5rem;font-family:'Barlow',sans-serif;font-size:.85rem;width:100%}
  .detail-field select:focus,.detail-field input:focus,.detail-field textarea:focus{outline:none;border-color:#f97316}
  .detail-field textarea{background:#1e293b;border:1px solid #334155;border-radius:4px;color:#e2e8f0;padding:.35rem .5rem;font-family:'Barlow',sans-serif;font-size:.85rem;width:100%;min-height:50px;resize:vertical}
"""

with open(template_path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Written {len(content)} chars to {template_path}")
