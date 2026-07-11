"use client";

import { useEffect, useState } from "react";

type AuthUser = { authenticated: boolean; email?: string | null; name?: string | null; picture?: string | null; role: string; oauth_configured?: boolean; lab_ids?: string[]; lab_names?: string[] };

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export default function AuthMenu() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [configured, setConfigured] = useState(false);
  const [theme, setTheme] = useState("light");
  const [language, setLanguage] = useState("zh-CN");

  useEffect(() => {
    const savedTheme = window.localStorage.getItem("radar-theme") || "light";
    const savedLanguage = window.localStorage.getItem("radar-language") || "zh-CN";
    setTheme(savedTheme); setLanguage(savedLanguage); document.body.dataset.theme = savedTheme; document.documentElement.lang = savedLanguage;
    fetch(`${apiBase}/api/auth/me`, { credentials: "include" })
      .then((response) => response.json())
      .then((value) => { setUser(value); setConfigured(value.authenticated); })
      .catch(() => setUser({ authenticated: false, role: "guest" }));
  }, []);

  function updateTheme(value: string) { setTheme(value); window.localStorage.setItem("radar-theme", value); document.body.dataset.theme = value; }
  function updateLanguage(value: string) { setLanguage(value); window.localStorage.setItem("radar-language", value); document.cookie = `radar-language=${value}; path=/; max-age=31536000`; document.documentElement.lang = value; window.location.reload(); }

  const initial = user?.name?.trim().charAt(0).toUpperCase() || user?.email?.charAt(0).toUpperCase() || "A";
  const labs = (user?.lab_ids || []).map((id, index) => ({ id, name: user?.lab_names?.[index] || id }));
  return <div className="topLinks"><a href="/">Dashboard</a>{configured && labs.length > 0 && <div className="myLabMenu"><a href={`/labs/${labs[0].id}`}>My Lab</a><div className="myLabDropdown" role="menu">{labs.map((lab) => <a href={`/labs/${lab.id}`} role="menuitem" key={lab.id}>{lab.name}</a>)}</div></div>}<div className="adminMenu"><button className="adminAvatarButton" type="button" aria-label="打开账户菜单" aria-haspopup="menu"><span className="adminAvatar">{initial}</span></button><div className="adminDropdown" role="menu">{configured ? <><div className="accountSummary"><strong>{user?.name || user?.email}</strong><small>{user?.role === "system_admin" ? "系统管理员" : "Lab 用户"}</small></div><label className="preferenceRow">系统语言<select value={language} onChange={(event) => updateLanguage(event.target.value)}><option value="zh-CN">中文</option><option value="en">English</option><option value="ja">日本語</option></select></label><label className="preferenceRow">页面风格<select value={theme} onChange={(event) => updateTheme(event.target.value)}><option value="light">亮色</option><option value="dark">深色</option></select></label>{user?.role === "system_admin" && <a href="/admin" role="menuitem">管理员控制台</a>}<button className="logoutButton" type="button" onClick={async () => { await fetch(`${apiBase}/api/auth/logout`, { method: "POST", credentials: "include" }); window.location.href = "/"; }}>退出登录</button></> : <a href={`${apiBase}/api/auth/google/start`} role="menuitem">Google 登录</a>}</div></div></div>;
}
