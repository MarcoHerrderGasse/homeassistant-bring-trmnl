#!/usr/bin/env python3
from flask import Flask, render_template_string, request, redirect, jsonify, send_from_directory
import json
import os
import time

_ADDON_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = "/data"
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
STATUS_FILE = os.path.join(DATA_DIR, ".status")
ITEMS_FILE = os.path.join(DATA_DIR, ".last_items")
LOG_FILE = os.path.join(DATA_DIR, "bring_trmnl.log")
TRIGGER_FILE = os.path.join(DATA_DIR, ".sync_trigger")

app = Flask(__name__)


def get_prefix():
    return request.headers.get("X-Ingress-Path", "").rstrip("/")


def read_config() -> dict:
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "bring_email": "", "bring_password": "", "list_uuid": "",
            "list_name": "", "trmnl_webhook_url": "",
            "poll_interval_minutes": 5, "webhook_interval_minutes": 30,
        }


def write_config(data: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)


def trigger_sync():
    try:
        with open(TRIGGER_FILE, "w") as f:
            f.write("1")
    except Exception:
        pass


def clear_status_error():
    status = read_status()
    if status.get("last_error"):
        status["last_error"] = None
        try:
            with open(STATUS_FILE, "w") as f:
                json.dump(status, f)
        except Exception:
            pass


def read_status() -> dict:
    try:
        with open(STATUS_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def read_items() -> list:
    try:
        with open(ITEMS_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def read_logs(lines: int = 150) -> str:
    try:
        with open(LOG_FILE) as f:
            all_lines = f.readlines()
        return "".join(all_lines[-lines:])
    except FileNotFoundError:
        return "Noch keine Logs vorhanden."


def fmt_ts(ts) -> str:
    if not ts:
        return "Noch nie"
    try:
        return time.strftime("%d.%m.%Y %H:%M", time.localtime(float(ts)))
    except Exception:
        return "–"


TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bring! → TRMNL</title>
<base href="{{ prefix }}/">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --ha-bg: #111111;
    --ha-sidebar: #1a1a1a;
    --ha-card: #1e1e1e;
    --ha-card-hover: #262626;
    --ha-border: rgba(255,255,255,0.12);
    --ha-border-strong: rgba(255,255,255,0.18);
    --ha-text: #e3e3e3;
    --ha-text-secondary: #9e9e9e;
    --ha-primary: #03a9f4;
    --ha-primary-dim: rgba(3,169,244,0.12);
    --ha-success: #4caf50;
    --ha-success-dim: rgba(76,175,80,0.12);
    --ha-error: #f44336;
    --ha-error-dim: rgba(244,67,54,0.12);
    --ha-warning: #ff9800;
    --ha-warning-dim: rgba(255,152,0,0.12);
    --ha-divider: rgba(255,255,255,0.08);
    --font: Roboto, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  }

  body {
    background: var(--ha-bg);
    color: var(--ha-text);
    font-family: var(--font);
    min-height: 100vh;
    display: flex;
    font-size: 14px;
    -webkit-font-smoothing: antialiased;
  }

  a { color: var(--ha-primary); text-decoration: none; }

  /* ── Sidebar ── */
  .sidebar {
    width: 256px;
    min-height: 100vh;
    background: var(--ha-sidebar);
    border-right: 1px solid var(--ha-border);
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
  }

  .sidebar-brand {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 0 16px;
    height: 64px;
    border-bottom: 1px solid var(--ha-border);
    flex-shrink: 0;
  }

  .brand-icon {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .brand-icon img { width: 32px; height: 32px; object-fit: contain; border-radius: 6px; }

  .brand-text {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .brand-title {
    font-size: 14px;
    font-weight: 500;
    color: var(--ha-text);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .brand-sub {
    font-size: 11px;
    color: var(--ha-text-secondary);
  }

  .nav { flex: 1; padding: 8px 0; }

  .nav-item {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 0 16px;
    height: 48px;
    color: var(--ha-text-secondary);
    font-size: 14px;
    font-weight: 400;
    text-decoration: none;
    position: relative;
    transition: background 0.15s, color 0.15s;
  }

  .nav-item:hover {
    background: rgba(255,255,255,0.05);
    color: var(--ha-text);
  }

  .nav-item.active {
    color: var(--ha-primary);
    background: var(--ha-primary-dim);
  }

  .nav-item.active::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 3px;
    background: var(--ha-primary);
  }

  .nav-icon {
    width: 20px;
    height: 20px;
    flex-shrink: 0;
    opacity: 0.7;
  }

  .nav-item.active .nav-icon { opacity: 1; }

  /* ── Content ── */
  .content {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
    overflow: auto;
  }

  .topbar {
    height: 64px;
    display: flex;
    align-items: center;
    padding: 0 24px;
    border-bottom: 1px solid var(--ha-border);
    flex-shrink: 0;
    gap: 12px;
    position: sticky;
    top: 0;
    z-index: 90;
    background: var(--ha-bg);
  }

  .topbar-title {
    font-size: 20px;
    font-weight: 400;
    color: var(--ha-text);
    flex: 1;
  }

  .topbar-logo {
    display: none;
    width: 28px;
    height: 28px;
    border-radius: 5px;
    flex-shrink: 0;
  }

  .main { padding: 24px; width: 100%; }

  /* ── Cards ── */
  .card {
    background: var(--ha-card);
    border: 1px solid var(--ha-border);
    margin-bottom: 16px;
    overflow: hidden;
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 20px 12px;
    border-bottom: 1px solid var(--ha-divider);
  }

  .card-header-title {
    font-size: 12px;
    font-weight: 500;
    color: var(--ha-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.8px;
  }

  .card-body { padding: 16px 20px; }
  .card-body-flush { padding: 0; }

  /* ── Stats ── */
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 0;
    margin-bottom: 16px;
    border: 1px solid var(--ha-border);
    background: var(--ha-border);
  }

  .stat-cell {
    background: var(--ha-card);
    padding: 16px 20px;
  }

  .stat-label {
    font-size: 11px;
    font-weight: 500;
    color: var(--ha-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.6px;
    margin-bottom: 8px;
  }

  .stat-value {
    font-size: 24px;
    font-weight: 300;
    line-height: 1.1;
    color: var(--ha-text);
  }

  .stat-value.md { font-size: 16px; font-weight: 400; padding-top: 4px; }

  .stat-sub {
    font-size: 12px;
    color: var(--ha-text-secondary);
    margin-top: 4px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  /* ── Badges ── */
  .badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    font-weight: 500;
  }

  .badge-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .badge-ok .badge-dot { background: var(--ha-success); }
  .badge-err .badge-dot { background: var(--ha-error); }
  .badge-warn .badge-dot { background: var(--ha-warning); }
  .badge-ok { color: var(--ha-success); }
  .badge-err { color: var(--ha-error); }
  .badge-warn { color: var(--ha-warning); }

  /* ── Buttons ── */
  .btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 0 16px;
    height: 36px;
    font-size: 14px;
    font-weight: 500;
    font-family: var(--font);
    cursor: pointer;
    border: none;
    letter-spacing: 0.3px;
    transition: background 0.15s, opacity 0.15s;
    text-decoration: none;
    white-space: nowrap;
  }

  .btn-primary {
    background: var(--ha-primary);
    color: #fff;
  }

  .btn-primary:hover { background: #29b6f6; }
  .btn-primary:disabled { opacity: 0.5; cursor: default; }

  .btn-outline {
    background: transparent;
    color: var(--ha-primary);
    border: 1px solid var(--ha-primary);
  }

  .btn-outline:hover { background: var(--ha-primary-dim); }
  .btn-outline:disabled { opacity: 0.5; cursor: default; }

  .btn-flat {
    background: transparent;
    color: var(--ha-text-secondary);
    border: 1px solid var(--ha-border-strong);
  }

  .btn-flat:hover { color: var(--ha-text); background: rgba(255,255,255,0.05); }

  .btn-sm { height: 30px; padding: 0 12px; font-size: 13px; }

  .actions { display: flex; gap: 8px; margin-bottom: 16px; }

  /* ── Items grid ── */
  .items-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
    gap: 0;
    background: var(--ha-divider);
  }

  .item-cell {
    background: var(--ha-card);
    padding: 16px 8px 12px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    text-align: center;
    border-right: 1px solid var(--ha-divider);
    border-bottom: 1px solid var(--ha-divider);
  }

  .item-icon { width: 40px; height: 40px; object-fit: contain; }
  .item-name { font-size: 12px; font-weight: 400; line-height: 1.3; }
  .item-section { font-size: 11px; color: var(--ha-text-secondary); }

  /* ── Forms ── */
  .form-section { margin-bottom: 0; }

  .form-section-header {
    padding: 14px 20px 10px;
    font-size: 12px;
    font-weight: 500;
    color: var(--ha-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.8px;
    border-bottom: 1px solid var(--ha-divider);
  }

  .form-body { padding: 20px; display: grid; gap: 16px; }
  .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .form-group { display: flex; flex-direction: column; gap: 6px; }

  .field-label {
    font-size: 12px;
    font-weight: 500;
    color: var(--ha-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  input[type=text], input[type=email], input[type=password], input[type=number] {
    background: rgba(0,0,0,0.25);
    border: 1px solid var(--ha-border-strong);
    border-radius: 0;
    color: var(--ha-text);
    font-size: 14px;
    font-family: var(--font);
    padding: 0 12px;
    height: 40px;
    outline: none;
    width: 100%;
    transition: border-color 0.15s;
  }

  input:focus {
    border-color: var(--ha-primary);
    background: rgba(3,169,244,0.04);
  }

  input::placeholder { color: var(--ha-text-secondary); opacity: 0.6; }

  .field-hint {
    font-size: 12px;
    color: var(--ha-text-secondary);
    opacity: 0.8;
  }

  .field-error {
    font-size: 12px;
    color: var(--ha-error);
  }

  /* ── List select ── */
  .list-select-row {
    display: flex;
    gap: 8px;
    align-items: stretch;
  }

  select {
    flex: 1;
    min-width: 0;
    background: rgba(0,0,0,0.25);
    border: 1px solid var(--ha-border-strong);
    border-radius: 0;
    color: var(--ha-text);
    font-size: 14px;
    font-family: var(--font);
    padding: 0 32px 0 12px;
    height: 40px;
    outline: none;
    cursor: pointer;
    appearance: none;
    -webkit-appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='%239e9e9e'%3E%3Cpath d='M7 10l5 5 5-5z'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 8px center;
    transition: border-color 0.15s;
  }

  select:focus { border-color: var(--ha-primary); background-color: rgba(3,169,244,0.04); }
  select:disabled { opacity: 0.5; cursor: not-allowed; }
  select option { background: #1e1e1e; color: var(--ha-text); }

  .list-select-row .btn { height: auto; align-self: stretch; }

  /* ── Alerts ── */
  .alert {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 12px 16px;
    font-size: 14px;
    margin-bottom: 16px;
    border-left: 3px solid;
  }

  .alert-ok {
    border-color: var(--ha-success);
    background: var(--ha-success-dim);
    color: var(--ha-success);
  }

  .alert-err {
    border-color: var(--ha-error);
    background: var(--ha-error-dim);
    color: var(--ha-error);
  }

  .alert a { color: inherit; text-decoration: underline; }

  .form-actions {
    padding: 16px 20px;
    border-top: 1px solid var(--ha-divider);
    display: flex;
    justify-content: flex-end;
    gap: 8px;
  }

  .webhook-row {
    display: flex;
    align-items: center;
    gap: 0;
    border-bottom: 1px solid var(--ha-divider);
  }

  .webhook-row:first-child { border-top: none; }

  .webhook-row .webhook-input {
    flex: 1;
    border: none;
    border-right: 1px solid var(--ha-divider);
    background: transparent;
    height: 44px;
    padding: 0 16px;
    font-size: 13px;
    border-radius: 0;
  }

  .webhook-row .webhook-input:focus {
    background: rgba(3,169,244,0.04);
    border-right-color: var(--ha-primary);
  }

  .webhook-remove {
    width: 44px;
    height: 44px;
    flex-shrink: 0;
    background: transparent;
    border: none;
    color: var(--ha-text-secondary);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: color 0.15s, background 0.15s;
  }

  .webhook-remove:hover { color: var(--ha-error); background: var(--ha-error-dim); }

  .divider { border: none; border-top: 1px solid var(--ha-divider); }
  .empty { color: var(--ha-text-secondary); font-size: 14px; text-align: center; padding: 32px 20px; }
  .log-box {
    background: rgba(0,0,0,0.4);
    border: 1px solid var(--ha-border);
    padding: 16px;
    font-family: 'Roboto Mono', 'Fira Code', 'SF Mono', monospace;
    font-size: 12px;
    color: var(--ha-text-secondary);
    white-space: pre-wrap;
    overflow: auto;
    max-height: 560px;
    line-height: 1.7;
  }

  .spinner {
    display: none;
    width: 14px;
    height: 14px;
    border: 2px solid rgba(255,255,255,0.2);
    border-top-color: var(--ha-primary);
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
    flex-shrink: 0;
  }

  @keyframes spin { to { transform: rotate(360deg); } }

  .chip {
    display: inline-flex;
    align-items: center;
    padding: 2px 8px;
    background: rgba(255,255,255,0.08);
    font-size: 12px;
    color: var(--ha-text-secondary);
  }

  /* ── Sidebar toggle / hamburger ── */
  .menu-btn {
    display: flex;
    background: transparent;
    border: none;
    color: var(--ha-text-secondary);
    cursor: pointer;
    width: 40px;
    height: 40px;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    transition: color 0.15s;
    padding: 0;
    margin-right: 4px;
  }
  .menu-btn:hover { color: var(--ha-text); }

  .sidebar-close {
    display: none;
    margin-left: auto;
    background: transparent;
    border: none;
    color: var(--ha-text-secondary);
    cursor: pointer;
    width: 36px;
    height: 36px;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    padding: 0;
  }
  .sidebar-close:hover { color: var(--ha-text); }

  /* ── Backdrop (mobile) ── */
  .backdrop {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.55);
    z-index: 199;
  }
  .backdrop.active { display: block; }

  /* ── Desktop sidebar collapse ── */
  .sidebar { transition: width 0.2s ease, transform 0.25s ease; overflow: hidden; }
  .sidebar.collapsed { width: 64px; }
  .sidebar.collapsed .brand-text { display: none; }
  .sidebar.collapsed .nav-label { display: none; }
  .sidebar.collapsed .sidebar-brand { justify-content: center; padding: 0 16px; }
  .sidebar.collapsed .nav-item { justify-content: center; padding: 0; gap: 0; }
  .sidebar.collapsed .nav-item.active::before { display: none; }
  .sidebar.collapsed .nav-icon { opacity: 1; }

  /* ── Mobile ── */
  @media (max-width: 768px) {
    .sidebar-close { display: flex; }

    /* Fix sticky topbar: body fills viewport, .content scrolls internally */
    body { height: 100vh; overflow: hidden; }
    .content { width: 100%; height: 100vh; overflow-x: hidden; overflow-y: auto; }

    .sidebar {
      position: fixed;
      top: 0; left: 0;
      height: 100vh;
      z-index: 200;
      transform: translateX(-100%);
      width: 280px;
    }
    .sidebar.open {
      transform: translateX(0);
      box-shadow: 8px 0 32px rgba(0,0,0,0.6);
    }

    .topbar { padding: 0 12px; height: 56px; }
    .topbar-title { font-size: 17px; }
    .topbar-logo { display: block; }
    .sync-label { display: none; }
    .btn-sync { width: 40px; padding: 0; flex-shrink: 0; }

    .main { padding: 12px 14px 40px; }

    .stats-grid { grid-template-columns: 1fr 1fr; }
    .stat-cell { padding: 12px 14px; }
    .stat-value { font-size: 20px; }
    .stat-value.md { font-size: 14px; }

    .form-row { grid-template-columns: 1fr; }
    .form-body { padding: 16px; }
    .form-actions { padding: 12px 16px; }

    .card-header { padding: 12px 16px 10px; }
    .card-body { padding: 12px 16px; }

    .items-grid { grid-template-columns: repeat(3, 1fr); }
    .item-cell { padding: 14px 6px 10px; }
    .item-icon { width: 36px; height: 36px; }
    .item-name { font-size: 13px; }
    .item-section { font-size: 11px; }

    .btn { height: 44px; min-width: 44px; }
    .btn-sm { height: 40px; }
    .actions { flex-wrap: wrap; }

    input[type=text], input[type=email], input[type=password], input[type=number],
    select {
      height: 48px;
      font-size: 16px;
    }

    .list-select-row { flex-direction: column; }
    .list-select-row select { width: 100%; flex: none; }
    .list-select-row .btn { width: 100%; }

    .webhook-row .webhook-input { height: 48px; font-size: 15px; }
    .webhook-remove { width: 48px; height: 48px; }

    .log-box { font-size: 11px; max-height: 360px; padding: 12px; }
  }

  @media (max-width: 400px) {
    .stats-grid { grid-template-columns: 1fr; }
  }
</style>
</head>
<body>

<div class="backdrop" id="backdrop" onclick="closeSidebar()"></div>

<nav class="sidebar" id="sidebar">
  <div class="sidebar-brand">
    <div class="brand-icon">
      <img src="bring-logo.svg" alt="Bring! TRMNL">
    </div>
    <div class="brand-text">
      <div class="brand-title">Bring! → TRMNL</div>
      <div class="brand-sub">Add-on</div>
    </div>
    <button class="sidebar-close" onclick="closeSidebar()" title="Sidebar schließen" aria-label="Sidebar schließen">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
    </button>
  </div>

  <div class="nav">
    <a href="" class="nav-item {% if page == 'dashboard' %}active{% endif %}" onclick="closeSidebar()">
      <svg class="nav-icon" viewBox="0 0 24 24" fill="currentColor"><path d="M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z"/></svg>
      <span class="nav-label">Dashboard</span>
    </a>
    <a href="settings" class="nav-item {% if page == 'settings' %}active{% endif %}" onclick="closeSidebar()">
      <svg class="nav-icon" viewBox="0 0 24 24" fill="currentColor"><path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58a.49.49 0 0 0 .12-.61l-1.92-3.32a.49.49 0 0 0-.59-.22l-2.39.96a7.02 7.02 0 0 0-1.62-.94l-.36-2.54a.484.484 0 0 0-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96a.47.47 0 0 0-.59.22L2.74 8.87a.48.48 0 0 0 .12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58a.49.49 0 0 0-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.37 1.04.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.57 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32a.47.47 0 0 0-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/></svg>
      <span class="nav-label">Einstellungen</span>
    </a>
    <a href="logs" class="nav-item {% if page == 'logs' %}active{% endif %}" onclick="closeSidebar()">
      <svg class="nav-icon" viewBox="0 0 24 24" fill="currentColor"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/></svg>
      <span class="nav-label">Logs</span>
    </a>
  </div>
</nav>

<div class="content">
  <div class="topbar">
    <button class="menu-btn" onclick="toggleSidebar()" title="Menü" aria-label="Menü">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/></svg>
    </button>
    <img src="bring-logo.svg" alt="" class="topbar-logo">
    <div class="topbar-title">
      {% if page == 'dashboard' %}Dashboard
      {% elif page == 'settings' %}Einstellungen
      {% elif page == 'logs' %}Logs
      {% endif %}
    </div>
    {% if page == 'dashboard' %}
    <form action="sync" method="post" style="margin:0">
      <button type="submit" class="btn btn-primary btn-sm btn-sync">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46A7.93 7.93 0 0 0 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74A7.93 7.93 0 0 0 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/></svg>
        <span class="sync-label">Jetzt synchronisieren</span>
      </button>
    </form>
    {% endif %}
  </div>

  <div class="main">

{% if page == 'dashboard' %}

  {% if not config_ok %}
  <div class="alert alert-err">
    Keine Konfiguration vorhanden –
    <a href="settings">Einstellungen</a> ausfüllen.
  </div>
  {% endif %}

  <div class="stats-grid">
    <div class="stat-cell">
      <div class="stat-label">Status</div>
      {% if status.last_error %}
        <div class="stat-value md"><span class="badge badge-err"><span class="badge-dot"></span>Fehler</span></div>
        <div class="stat-sub" style="color:var(--ha-error)">{{ status.last_error }}</div>
      {% else %}
        <div class="stat-value md"><span class="badge badge-ok"><span class="badge-dot"></span>Aktiv</span></div>
      {% endif %}
    </div>
    <div class="stat-cell">
      <div class="stat-label">Artikel</div>
      <div class="stat-value">{{ items | length }}</div>
    </div>
    <div class="stat-cell">
      <div class="stat-label">Letzter Push</div>
      <div class="stat-value md">{{ last_push }}</div>
      {% if status.last_reason %}<div class="stat-sub">{{ status.last_reason }}</div>{% endif %}
    </div>
    <div class="stat-cell">
      <div class="stat-label">Aktive Liste</div>
      <div class="stat-value md">{{ cfg.list_name or "–" }}</div>
      <div class="stat-sub">{{ cfg.bring_email }}</div>
    </div>
  </div>

  <div class="card">
    <div class="card-header">
      <div class="card-header-title">Einkaufsliste</div>
      <span class="chip">{{ items | length }} Artikel</span>
    </div>
    {% if items %}
    <div class="card-body-flush">
      <div class="items-grid">
        {% for item in items %}
        <div class="item-cell">
          <img class="item-icon"
               src="https://web.getbring.com/assets/images/items/{{ item.icon }}"
               onerror="this.src='https://web.getbring.com/assets/images/items/a.png'"
               alt="{{ item.display }}">
          <div class="item-name">{{ item.display }}</div>
          {% if item.section %}<div class="item-section">{{ item.section }}</div>{% endif %}
        </div>
        {% endfor %}
      </div>
    </div>
    {% else %}
    <div class="card-body">
      {% if fresh %}
      <div class="empty" id="syncWait">
        <div style="display:flex;align-items:center;justify-content:center;gap:10px">
          <div class="spinner" style="display:inline-block;border-top-color:var(--ha-primary)"></div>
          Erster Sync läuft – wird automatisch aktualisiert…
        </div>
      </div>
      {% else %}
      <div class="empty">Noch keine Artikel – klicke auf "Jetzt synchronisieren".</div>
      {% endif %}
    </div>
    {% endif %}
  </div>

  {% if fresh and not items %}
  <script>
  (function poll() {
    fetch('api/status').then(r => r.json()).then(d => {
      if (d.item_count > 0) { window.location.href = window.location.pathname; return; }
      setTimeout(poll, 2500);
    }).catch(() => setTimeout(poll, 3000));
  })();
  </script>
  {% endif %}

{% elif page == 'settings' %}

  {% if saved %}
  <div class="alert alert-ok">Einstellungen gespeichert. Synchronisierung läuft sofort an.</div>
  {% endif %}

  <form method="post" action="settings" id="settingsForm">

    <div class="card">
      <div class="form-section-header">Bring! Zugangsdaten</div>
      <div class="form-body">
        <div class="form-row">
          <div class="form-group">
            <div class="field-label">E-Mail</div>
            <input type="email" name="bring_email" id="email" value="{{ cfg.bring_email }}" placeholder="deine@email.de" autocomplete="off">
          </div>
          <div class="form-group">
            <div class="field-label">Passwort</div>
            <input type="password" name="bring_password" id="password" value="{{ cfg.bring_password }}" placeholder="••••••••" autocomplete="new-password">
          </div>
        </div>

        <div class="form-group">
          <div class="field-label">Einkaufsliste</div>
          <div class="list-select-row">
            <select id="listSelect" onchange="onListChange(this)">
              {% if cfg.list_name %}
              <option value="{{ cfg.list_uuid }}" data-name="{{ cfg.list_name }}" selected>{{ cfg.list_name }}</option>
              {% else %}
              <option value="" disabled selected>Noch keine Liste ausgewählt</option>
              {% endif %}
            </select>
            <button type="button" class="btn btn-outline btn-sm" id="fetchBtn" onclick="fetchLists()">
              <div class="spinner" id="spinner"></div>
              <span id="fetchLabel">Listen laden</span>
            </button>
          </div>
          <div id="listSaveHint" style="display:none; margin-top:10px;">
            <button type="submit" class="btn btn-primary btn-sm">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M17 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V7l-4-4zm-5 16a3 3 0 1 1 0-6 3 3 0 0 1 0 6zm3-10H5V5h10v4z"/></svg>
              Liste speichern
            </button>
          </div>
          <div class="field-error" id="listError"></div>
          <div class="field-hint">Klicke auf "Listen laden" um alle verfügbaren Bring!-Listen zu laden.</div>
        </div>

        <input type="hidden" name="list_uuid" id="listUuid" value="{{ cfg.list_uuid }}">
        <input type="hidden" name="list_name" id="listName" value="{{ cfg.list_name }}">
      </div>
    </div>

    <div class="card">
      <div class="form-section-header">TRMNL Webhook</div>
      <div class="form-body" style="gap:0;padding:0">
        <div id="webhookList" data-urls="{{ cfg.trmnl_webhook_url | e }}"></div>
        <div style="padding:12px 20px;border-top:1px solid var(--ha-divider)">
          <button type="button" class="btn btn-flat btn-sm" onclick="addWebhookRow('')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
            Webhook hinzufügen
          </button>
        </div>
      </div>
      <input type="hidden" name="trmnl_webhook_url" id="webhookHidden">
    </div>

    <div class="card">
      <div class="form-section-header">Synchronisierungsintervalle</div>
      <div class="form-body">
        <div class="form-row">
          <div class="form-group">
            <div class="field-label">Prüfintervall (Minuten)</div>
            <input type="number" name="poll_interval_minutes" value="{{ cfg.poll_interval_minutes }}" min="1" max="60">
            <div class="field-hint">Wie oft Bring! auf Änderungen geprüft wird.</div>
          </div>
          <div class="form-group">
            <div class="field-label">Erzwungener Push (Minuten)</div>
            <input type="number" name="webhook_interval_minutes" value="{{ cfg.webhook_interval_minutes }}" min="1" max="1440">
            <div class="field-hint">Maximaler Abstand zwischen Pushes, auch ohne Listenänderung.</div>
          </div>
        </div>
      </div>
    </div>

    <div style="padding: 20px 0 4px; display: flex; justify-content: flex-end;">
      <button type="submit" class="btn btn-primary">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M17 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V7l-4-4zm-5 16a3 3 0 1 1 0-6 3 3 0 0 1 0 6zm3-10H5V5h10v4z"/></svg>
        Speichern &amp; synchronisieren
      </button>
    </div>

  </form>

  <script>
  function addWebhookRow(url) {
    const list = document.getElementById('webhookList');
    const row = document.createElement('div');
    row.className = 'webhook-row';
    row.innerHTML =
      '<input type="text" class="webhook-input" value="' + url.replace(/"/g, '&quot;') + '" placeholder="https://usetrmnl.com/api/custom_plugins/...">' +
      '<button type="button" class="webhook-remove" onclick="removeWebhookRow(this)" title="Entfernen">' +
      '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>' +
      '</button>';
    list.appendChild(row);
  }

  function removeWebhookRow(btn) {
    const list = document.getElementById('webhookList');
    if (list.children.length > 1) {
      btn.closest('.webhook-row').remove();
    } else {
      btn.closest('.webhook-row').querySelector('.webhook-input').value = '';
    }
  }

  (function initWebhooks() {
    const raw = document.getElementById('webhookList').dataset.urls || '';
    const urls = raw.split(',').map(s => s.trim()).filter(Boolean);
    if (urls.length === 0) urls.push('');
    urls.forEach(u => addWebhookRow(u));

    document.getElementById('settingsForm').addEventListener('submit', function() {
      const vals = Array.from(document.querySelectorAll('.webhook-input'))
        .map(i => i.value.trim()).filter(Boolean);
      document.getElementById('webhookHidden').value = vals.join(',');
    });
  })();

  function onListChange(sel) {
    const opt = sel.options[sel.selectedIndex];
    document.getElementById('listUuid').value = sel.value;
    document.getElementById('listName').value = opt.dataset.name || opt.text;
    document.getElementById('listSaveHint').style.display = 'block';
  }

  function renderLists(lists) {
    const sel = document.getElementById('listSelect');
    const currentUuid = document.getElementById('listUuid').value;
    sel.innerHTML = '';
    if (!lists || lists.length === 0) {
      const opt = document.createElement('option');
      opt.disabled = true; opt.selected = true;
      opt.textContent = 'Keine Listen gefunden';
      sel.appendChild(opt);
      return;
    }
    lists.forEach(l => {
      const opt = document.createElement('option');
      opt.value = l.uuid;
      opt.dataset.name = l.name;
      opt.textContent = l.name;
      opt.selected = l.uuid === currentUuid;
      sel.appendChild(opt);
    });
  }

  async function fetchLists(silent) {
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value.trim();
    const errEl = document.getElementById('listError');
    if (!silent) errEl.textContent = '';

    if (!email || !password) {
      if (!silent) errEl.textContent = 'Bitte zuerst E-Mail und Passwort eingeben.';
      return;
    }

    document.getElementById('spinner').style.display = 'inline-block';
    document.getElementById('fetchLabel').textContent = 'Laden…';
    document.getElementById('fetchBtn').disabled = true;
    document.getElementById('listSelect').disabled = true;

    try {
      const resp = await fetch('api/lists?email=' + encodeURIComponent(email) + '&password=' + encodeURIComponent(password));
      const data = await resp.json();
      if (!resp.ok) {
        if (!silent) errEl.textContent = data.error || 'Fehler beim Laden.';
        return;
      }
      renderLists(data.lists);
    } catch(e) {
      if (!silent) errEl.textContent = 'Netzwerkfehler: ' + e.message;
    } finally {
      document.getElementById('spinner').style.display = 'none';
      document.getElementById('fetchLabel').textContent = 'Aktualisieren';
      document.getElementById('fetchBtn').disabled = false;
      document.getElementById('listSelect').disabled = false;
    }
  }

  // Auto-load lists if credentials are already saved
  (function() {
    const email = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value.trim();
    if (email && password) fetchLists(true);
  })();
  </script>

{% elif page == 'logs' %}

  <div class="actions">
    <a href="logs" class="btn btn-flat btn-sm">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M17.65 6.35A7.958 7.958 0 0 0 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08A5.99 5.99 0 0 1 12 18c-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/></svg>
      Aktualisieren
    </a>
  </div>
  <div class="log-box" id="lb">{{ logs }}</div>
  <script>document.getElementById('lb').scrollTop = 99999;</script>

{% endif %}

  </div>
</div>

<script>
(function() {
  var sidebar = document.getElementById('sidebar');
  var backdrop = document.getElementById('backdrop');
  var isMobile = function() { return window.innerWidth <= 768; };

  window.toggleSidebar = function() {
    if (isMobile()) {
      var open = sidebar.classList.toggle('open');
      backdrop.classList.toggle('active', open);
      document.body.style.overflow = open ? 'hidden' : '';
    } else {
      sidebar.classList.toggle('collapsed');
      try { localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed') ? '1' : '0'); } catch(e) {}
    }
  };

  window.closeSidebar = function() {
    if (isMobile()) {
      sidebar.classList.remove('open');
      backdrop.classList.remove('active');
      document.body.style.overflow = '';
    }
  };

  // Restore desktop collapsed state
  try {
    if (!isMobile() && localStorage.getItem('sidebarCollapsed') === '1') {
      sidebar.classList.add('collapsed');
    }
  } catch(e) {}

  // On resize: clean up mobile state if switching to desktop
  window.addEventListener('resize', function() {
    if (!isMobile()) {
      sidebar.classList.remove('open');
      backdrop.classList.remove('active');
      document.body.style.overflow = '';
    }
  });
})();
</script>

</body>
</html>"""


SETUP_TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bring! → TRMNL · Einrichtung</title>
<base href="{{ prefix }}/">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --ha-bg: #111111;
    --ha-card: #1e1e1e;
    --ha-border: rgba(255,255,255,0.12);
    --ha-border-strong: rgba(255,255,255,0.18);
    --ha-text: #e3e3e3;
    --ha-text-secondary: #9e9e9e;
    --ha-primary: #03a9f4;
    --ha-primary-dim: rgba(3,169,244,0.12);
    --ha-success: #4caf50;
    --ha-success-dim: rgba(76,175,80,0.12);
    --ha-error: #f44336;
    --ha-error-dim: rgba(244,67,54,0.12);
    --ha-divider: rgba(255,255,255,0.08);
    --font: Roboto, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  }
  body {
    background: var(--ha-bg);
    color: var(--ha-text);
    font-family: var(--font);
    min-height: 100vh;
    display: flex;
    align-items: flex-start;
    justify-content: center;
    padding: 48px 16px 64px;
    font-size: 14px;
    -webkit-font-smoothing: antialiased;
  }
  .wizard { width: 100%; max-width: 520px; }

  /* Header */
  .wiz-header { text-align: center; margin-bottom: 36px; }
  .wiz-logo { display: inline-flex; align-items: center; gap: 10px; margin-bottom: 8px; }
  .wiz-logo-icon {
    display: flex; align-items: center; justify-content: center; flex-shrink: 0;
  }
  .wiz-title { font-size: 20px; font-weight: 400; color: var(--ha-text); }
  .wiz-subtitle { font-size: 13px; color: var(--ha-text-secondary); margin-top: 4px; line-height: 1.5; }

  /* Progress */
  .steps { display: flex; align-items: center; margin-bottom: 28px; }
  .step-wrap { flex: 1; display: flex; align-items: center; }
  .step-wrap:last-child { flex: 0; }
  .step-dot {
    width: 30px; height: 30px; border-radius: 50%;
    border: 2px solid var(--ha-border-strong);
    display: flex; align-items: center; justify-content: center;
    font-size: 12px; font-weight: 500; color: var(--ha-text-secondary);
    background: var(--ha-bg); flex-shrink: 0; position: relative; z-index: 1;
    transition: border-color 0.3s, background 0.3s, color 0.3s, box-shadow 0.3s;
  }
  .step-dot.active { border-color: var(--ha-primary); color: var(--ha-primary); box-shadow: 0 0 0 4px var(--ha-primary-dim); }
  .step-dot.done { border-color: var(--ha-success); background: var(--ha-success); color: #fff; }
  .step-line { flex: 1; height: 2px; background: var(--ha-border-strong); margin: 0 6px; transition: background 0.4s; }
  .step-line.done { background: var(--ha-success); }
  .step-label { font-size: 11px; color: var(--ha-text-secondary); text-align: center; margin-top: 6px; }

  /* Panels */
  .panels { position: relative; }
  .panel { display: none; }
  .panel.active { display: block; animation: slideIn 0.22s ease; }
  .panel.back-active { display: block; animation: slideBack 0.22s ease; }
  @keyframes slideIn { from { opacity: 0; transform: translateX(16px); } to { opacity: 1; transform: translateX(0); } }
  @keyframes slideBack { from { opacity: 0; transform: translateX(-16px); } to { opacity: 1; transform: translateX(0); } }

  /* Card */
  .card { background: var(--ha-card); border: 1px solid var(--ha-border); overflow: hidden; }
  .card-hd { padding: 18px 20px 14px; border-bottom: 1px solid var(--ha-divider); }
  .card-hd-title { font-size: 15px; font-weight: 500; color: var(--ha-text); }
  .card-hd-desc { font-size: 13px; color: var(--ha-text-secondary); margin-top: 4px; line-height: 1.5; }
  .card-bd { padding: 20px; display: grid; gap: 16px; }
  .card-ft {
    display: flex; align-items: center; justify-content: space-between;
    padding: 14px 20px; border-top: 1px solid var(--ha-divider);
  }

  /* Forms */
  .fg { display: flex; flex-direction: column; gap: 6px; }
  .fl { font-size: 12px; font-weight: 500; color: var(--ha-text-secondary); text-transform: uppercase; letter-spacing: 0.5px; }
  input[type=text], input[type=email], input[type=password], input[type=number] {
    background: rgba(0,0,0,0.25); border: 1px solid var(--ha-border-strong); border-radius: 0;
    color: var(--ha-text); font-size: 14px; font-family: var(--font);
    padding: 0 12px; height: 40px; outline: none; width: 100%; transition: border-color 0.15s;
  }
  input:focus { border-color: var(--ha-primary); background: rgba(3,169,244,0.04); }
  input::placeholder { color: var(--ha-text-secondary); opacity: 0.6; }
  .fh { font-size: 12px; color: var(--ha-text-secondary); opacity: 0.8; line-height: 1.4; }
  .fe { font-size: 12px; color: var(--ha-error); min-height: 16px; }

  /* Buttons */
  .btn {
    display: inline-flex; align-items: center; justify-content: center; gap: 8px;
    padding: 0 20px; height: 38px; font-size: 14px; font-weight: 500;
    font-family: var(--font); cursor: pointer; border: none;
    transition: background 0.15s, opacity 0.15s; white-space: nowrap;
  }
  .btn-primary { background: var(--ha-primary); color: #fff; }
  .btn-primary:hover { background: #29b6f6; }
  .btn-primary:disabled { opacity: 0.5; cursor: default; }
  .btn-flat { background: transparent; color: var(--ha-text-secondary); border: 1px solid var(--ha-border-strong); }
  .btn-flat:hover { color: var(--ha-text); background: rgba(255,255,255,0.05); }

  /* List grid (step 2) */
  .list-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  .list-card {
    background: rgba(0,0,0,0.2); border: 2px solid var(--ha-border-strong);
    padding: 14px; cursor: pointer; display: flex; align-items: center; gap: 10px;
    transition: border-color 0.15s, background 0.15s; position: relative;
  }
  .list-card:hover { border-color: rgba(3,169,244,0.45); background: var(--ha-primary-dim); }
  .list-card.selected { border-color: var(--ha-primary); background: var(--ha-primary-dim); }
  .list-card-ico {
    width: 34px; height: 34px; background: rgba(255,255,255,0.06);
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0; color: var(--ha-text-secondary);
  }
  .list-card.selected .list-card-ico { background: var(--ha-primary-dim); color: var(--ha-primary); }
  .list-card-name { font-size: 13px; flex: 1; line-height: 1.3; word-break: break-word; }
  .list-card-chk {
    position: absolute; top: 6px; right: 6px; width: 16px; height: 16px;
    background: var(--ha-primary); display: flex; align-items: center; justify-content: center;
    opacity: 0; transition: opacity 0.15s;
  }
  .list-card.selected .list-card-chk { opacity: 1; }
  .list-card-chk svg { width: 10px; height: 10px; fill: #fff; }
  .list-empty { padding: 28px; text-align: center; color: var(--ha-text-secondary); font-size: 13px; }

  /* Spinner */
  .sp {
    display: inline-block; width: 14px; height: 14px;
    border: 2px solid rgba(255,255,255,0.2); border-top-color: var(--ha-primary);
    border-radius: 50%; animation: spin 0.7s linear infinite; flex-shrink: 0;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  @media (max-width: 420px) {
    .list-grid { grid-template-columns: 1fr; }
    body { padding: 24px 12px 48px; }
  }
</style>
</head>
<body>
<div class="wizard">

  <div class="wiz-header">
    <div class="wiz-logo">
      <div class="wiz-logo-icon">
        <img src="bring-logo.svg" alt="Bring! TRMNL" width="40" height="40" style="border-radius:8px;display:block;">
      </div>
      <span class="wiz-title">Bring! → TRMNL</span>
    </div>
    <div class="wiz-subtitle">Einrichtungsassistent – wenige Schritte bis zur ersten Synchronisierung</div>
  </div>

  <div class="steps">
    <div class="step-wrap">
      <div class="step-dot active" id="dot-1">1</div>
      <div class="step-line" id="line-1"></div>
    </div>
    <div class="step-wrap">
      <div class="step-dot" id="dot-2">2</div>
      <div class="step-line" id="line-2"></div>
    </div>
    <div class="step-wrap">
      <div class="step-dot" id="dot-3">3</div>
      <div class="step-line" id="line-3"></div>
    </div>
    <div class="step-wrap">
      <div class="step-dot" id="dot-4">4</div>
    </div>
  </div>

  <div class="panels">

    <!-- Step 1: Login -->
    <div class="panel active" id="panel-1">
      <div class="card">
        <div class="card-hd">
          <div class="card-hd-title">Bring! Zugangsdaten</div>
          <div class="card-hd-desc">Melde dich mit deinem Bring!-Konto an, um deine Einkaufslisten zu laden.</div>
        </div>
        <div class="card-bd">
          <div class="fg">
            <div class="fl">E-Mail</div>
            <input type="email" id="s1Email" placeholder="deine@email.de" autocomplete="email">
          </div>
          <div class="fg">
            <div class="fl">Passwort</div>
            <input type="password" id="s1Password" placeholder="••••••••" autocomplete="current-password">
          </div>
          <div class="fe" id="s1Error"></div>
        </div>
        <div class="card-ft">
          <div></div>
          <button class="btn btn-primary" id="s1Btn" onclick="step1Next()">
            <span id="s1Label">Anmelden &amp; weiter</span>
            <span class="sp" id="s1Sp" style="display:none"></span>
          </button>
        </div>
      </div>
    </div>

    <!-- Step 2: List selection -->
    <div class="panel" id="panel-2">
      <div class="card">
        <div class="card-hd">
          <div class="card-hd-title">Einkaufsliste auswählen</div>
          <div class="card-hd-desc">Wähle die Liste, die auf deinem TRMNL-Display erscheinen soll.</div>
        </div>
        <div class="card-bd" style="gap:8px">
          <div id="listGrid"></div>
          <div class="fe" id="s2Error"></div>
        </div>
        <div class="card-ft">
          <button class="btn btn-flat" onclick="goTo(1,'back')">← Zurück</button>
          <button class="btn btn-primary" onclick="step2Next()">Weiter →</button>
        </div>
      </div>
    </div>

    <!-- Step 3: Webhook -->
    <div class="panel" id="panel-3">
      <div class="card">
        <div class="card-hd">
          <div class="card-hd-title">TRMNL Webhook</div>
          <div class="card-hd-desc">Die Webhook-URL findest du im TRMNL-Dashboard unter Custom Plugins.</div>
        </div>
        <div class="card-bd">
          <div class="fg">
            <div class="fl">Webhook-URL</div>
            <input type="text" id="s3Webhook" placeholder="https://usetrmnl.com/api/custom_plugins/...">
            <div class="fh">Mehrere URLs mit Komma trennen, falls du mehrere Geräte hast.</div>
          </div>
          <div class="fe" id="s3Error"></div>
        </div>
        <div class="card-ft">
          <button class="btn btn-flat" onclick="goTo(2,'back')">← Zurück</button>
          <button class="btn btn-primary" onclick="step3Next()">Weiter →</button>
        </div>
      </div>
    </div>

    <!-- Step 4: Intervals + finish -->
    <div class="panel" id="panel-4">
      <div class="card">
        <div class="card-hd">
          <div class="card-hd-title">Synchronisierungsintervalle</div>
          <div class="card-hd-desc">Lege fest, wie oft Bring! geprüft wird und wie oft das Display spätestens aktualisiert wird.</div>
        </div>
        <div class="card-bd">
          <div class="fg">
            <div class="fl">Prüfintervall (Minuten)</div>
            <input type="number" id="s4Poll" value="5" min="1" max="60">
            <div class="fh">Wie oft die Bring!-Liste auf Änderungen geprüft wird.</div>
          </div>
          <div class="fg">
            <div class="fl">Erzwungener Push (Minuten)</div>
            <input type="number" id="s4Interval" value="30" min="1" max="1440">
            <div class="fh">Maximaler Abstand zwischen Pushes, auch ohne Listenänderung.</div>
          </div>
          <div class="fe" id="s4Error"></div>
        </div>
        <div class="card-ft">
          <button class="btn btn-flat" onclick="goTo(3,'back')">← Zurück</button>
          <button class="btn btn-primary" id="s4Btn" onclick="finish()">
            <span id="s4Label">Setup abschließen</span>
            <span class="sp" id="s4Sp" style="display:none"></span>
          </button>
        </div>
      </div>
    </div>

  </div>
</div>

<script>
let currentStep = 1;
let fetchedLists = [];
let selectedList = null;
let authEmail = '';
let authPassword = '';

const CHECK_SVG = '<svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/></svg>';
const LIST_SVG = '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M3 13h2v-2H3v2zm0 4h2v-2H3v2zm0-8h2V7H3v2zm4 4h14v-2H7v2zm0 4h14v-2H7v2zM7 7v2h14V7H7z"/></svg>';

function goTo(step, dir) {
  const from = document.getElementById('panel-' + currentStep);
  const to   = document.getElementById('panel-' + step);
  from.classList.remove('active', 'back-active');
  to.classList.add(dir === 'back' ? 'back-active' : 'active');
  updateDots(step);
  currentStep = step;
}

function updateDots(step) {
  for (let i = 1; i <= 4; i++) {
    const dot = document.getElementById('dot-' + i);
    dot.classList.remove('active', 'done');
    if (i < step) {
      dot.classList.add('done');
      dot.innerHTML = CHECK_SVG;
    } else {
      dot.classList.toggle('active', i === step);
      dot.textContent = i;
    }
    if (i < 4) document.getElementById('line-' + i).classList.toggle('done', i < step);
  }
}

async function step1Next() {
  const email = document.getElementById('s1Email').value.trim();
  const pw    = document.getElementById('s1Password').value.trim();
  const err   = document.getElementById('s1Error');
  err.textContent = '';
  if (!email || !pw) { err.textContent = 'Bitte E-Mail und Passwort eingeben.'; return; }

  setBusy('s1Btn', 's1Label', 's1Sp', 'Anmelden…');
  try {
    const resp = await fetch('api/lists?email=' + encodeURIComponent(email) + '&password=' + encodeURIComponent(pw));
    const data = await resp.json();
    if (!resp.ok) { err.textContent = data.error || 'Login fehlgeschlagen.'; return; }
    fetchedLists = data.lists || [];
    authEmail    = email;
    authPassword = pw;
    renderListGrid();
    goTo(2);
  } catch(e) {
    err.textContent = 'Netzwerkfehler: ' + e.message;
  } finally {
    setIdle('s1Btn', 's1Label', 's1Sp', 'Anmelden &amp; weiter');
  }
}

function renderListGrid() {
  const container = document.getElementById('listGrid');
  if (!fetchedLists.length) {
    container.innerHTML = '<div class="list-empty">Keine Listen in diesem Konto gefunden.</div>';
    return;
  }
  const grid = document.createElement('div');
  grid.className = 'list-grid';
  fetchedLists.forEach(l => {
    const card = document.createElement('div');
    card.className = 'list-card' + (selectedList && selectedList.uuid === l.uuid ? ' selected' : '');
    card.innerHTML =
      '<div class="list-card-ico">' + LIST_SVG + '</div>' +
      '<div class="list-card-name">' + esc(l.name) + '</div>' +
      '<div class="list-card-chk">' + CHECK_SVG + '</div>';
    card.addEventListener('click', () => {
      document.querySelectorAll('.list-card').forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');
      selectedList = l;
      document.getElementById('s2Error').textContent = '';
    });
    grid.appendChild(card);
  });
  container.innerHTML = '';
  container.appendChild(grid);
}

function step2Next() {
  if (!selectedList) { document.getElementById('s2Error').textContent = 'Bitte eine Liste auswählen.'; return; }
  document.getElementById('s2Error').textContent = '';
  goTo(3);
}

function step3Next() {
  const v = document.getElementById('s3Webhook').value.trim();
  if (!v) { document.getElementById('s3Error').textContent = 'Bitte eine Webhook-URL eingeben.'; return; }
  document.getElementById('s3Error').textContent = '';
  goTo(4);
}

function finish() {
  const poll     = parseInt(document.getElementById('s4Poll').value) || 5;
  const interval = parseInt(document.getElementById('s4Interval').value) || 30;
  const err      = document.getElementById('s4Error');
  if (poll < 1 || interval < 1) { err.textContent = 'Intervalle müssen mindestens 1 Minute betragen.'; return; }
  err.textContent = '';

  setBusy('s4Btn', 's4Label', 's4Sp', 'Wird gespeichert…');

  const form = document.createElement('form');
  form.method = 'POST';
  form.action = 'setup';
  const fields = {
    bring_email: authEmail,
    bring_password: authPassword,
    list_uuid: selectedList.uuid,
    list_name: selectedList.name,
    trmnl_webhook_url: document.getElementById('s3Webhook').value.trim(),
    poll_interval_minutes: poll,
    webhook_interval_minutes: interval,
  };
  Object.entries(fields).forEach(([k, v]) => {
    const inp = document.createElement('input');
    inp.type = 'hidden'; inp.name = k; inp.value = v;
    form.appendChild(inp);
  });
  document.body.appendChild(form);
  form.submit();
}

function setBusy(btn, lbl, sp, text) {
  document.getElementById(btn).disabled = true;
  document.getElementById(lbl).textContent = text;
  document.getElementById(sp).style.display = 'inline-block';
}
function setIdle(btn, lbl, sp, html) {
  document.getElementById(btn).disabled = false;
  document.getElementById(lbl).innerHTML = html;
  document.getElementById(sp).style.display = 'none';
}
function esc(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

document.getElementById('s1Password').addEventListener('keydown', e => { if (e.key === 'Enter') step1Next(); });
document.getElementById('s1Email').addEventListener('keydown',    e => { if (e.key === 'Enter') step1Next(); });
</script>
</body>
</html>"""


@app.route("/")
def dashboard():
    prefix = get_prefix()
    cfg = read_config()
    config_ok = bool(cfg.get("bring_email") and cfg.get("bring_password") and cfg.get("trmnl_webhook_url"))
    if not config_ok:
        return redirect(f"{prefix}/setup")
    status = read_status()
    items = read_items()
    fresh = request.args.get("fresh") == "1"
    return render_template_string(
        TEMPLATE, page="dashboard", prefix=prefix,
        config_ok=config_ok, status=status, items=items, cfg=cfg,
        last_push=fmt_ts(status.get("last_push_ts")),
        fresh=fresh,
    )


@app.route("/setup", methods=["GET", "POST"])
def setup():
    prefix = get_prefix()
    if request.method == "POST":
        write_config({
            "bring_email": request.form.get("bring_email", "").strip(),
            "bring_password": request.form.get("bring_password", "").strip(),
            "list_uuid": request.form.get("list_uuid", "").strip(),
            "list_name": request.form.get("list_name", "").strip(),
            "trmnl_webhook_url": request.form.get("trmnl_webhook_url", "").strip(),
            "poll_interval_minutes": int(request.form.get("poll_interval_minutes") or 5),
            "webhook_interval_minutes": int(request.form.get("webhook_interval_minutes") or 30),
        })
        clear_status_error()
        trigger_sync()
        return redirect(f"{prefix}/?fresh=1")
    return render_template_string(SETUP_TEMPLATE, prefix=prefix)


@app.route("/settings", methods=["GET", "POST"])
def settings():
    prefix = get_prefix()
    saved = False
    if request.method == "POST":
        write_config({
            "bring_email": request.form.get("bring_email", "").strip(),
            "bring_password": request.form.get("bring_password", "").strip(),
            "list_uuid": request.form.get("list_uuid", "").strip(),
            "list_name": request.form.get("list_name", "").strip(),
            "trmnl_webhook_url": request.form.get("trmnl_webhook_url", "").strip(),
            "poll_interval_minutes": int(request.form.get("poll_interval_minutes") or 5),
            "webhook_interval_minutes": int(request.form.get("webhook_interval_minutes") or 30),
        })
        clear_status_error()
        trigger_sync()
        saved = True
    cfg = read_config()
    return render_template_string(
        TEMPLATE, page="settings", prefix=prefix, cfg=cfg, saved=saved,
        status={}, items=[],
    )


@app.route("/logs")
def logs():
    prefix = get_prefix()
    cfg = read_config()
    return render_template_string(
        TEMPLATE, page="logs", prefix=prefix, cfg=cfg,
        logs=read_logs(), status={}, items=[],
    )


@app.route("/sync", methods=["POST"])
def sync():
    prefix = get_prefix()
    trigger_sync()
    return redirect(f"{prefix}/")


@app.route("/api/lists")
def api_lists():
    email = request.args.get("email", "")
    password = request.args.get("password", "")
    if not email or not password:
        return jsonify({"error": "Zugangsdaten fehlen"}), 400
    try:
        from bring_api import authenticate, fetch_all_lists
        token, user_uuid = authenticate(email, password)
        if not token:
            return jsonify({"error": "Login fehlgeschlagen – E-Mail oder Passwort falsch"}), 401
        lists = fetch_all_lists(token, user_uuid)
        return jsonify({"lists": [{"uuid": l["listUuid"], "name": l["name"]} for l in lists]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/icon.png")
def addon_icon():
    return send_from_directory(_ADDON_DIR, "icon.png")


@app.route("/bring-logo.svg")
def addon_logo_svg():
    return send_from_directory(_ADDON_DIR, "bring-logo.svg", mimetype="image/svg+xml")


@app.route("/api/status")
def api_status():
    status = read_status()
    return jsonify({**status, "item_count": len(read_items())})


if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    app.run(host="0.0.0.0", port=8099, debug=False)
