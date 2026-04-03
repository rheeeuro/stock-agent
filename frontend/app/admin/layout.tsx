"use client";

import { useState, useEffect, FormEvent } from "react";
import { Lock } from "lucide-react";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [authenticated, setAuthenticated] = useState(false);
  const [checking, setChecking] = useState(true);
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const saved = sessionStorage.getItem("admin_auth");
    if (saved === "true") {
      setAuthenticated(true);
    }
    setChecking(false);
  }, []);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await fetch("/api/admin/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      if (res.ok) {
        sessionStorage.setItem("admin_auth", "true");
        setAuthenticated(true);
      } else {
        setError("비밀번호가 올바르지 않습니다.");
      }
    } catch {
      setError("서버에 연결할 수 없습니다.");
    } finally {
      setLoading(false);
    }
  };

  if (checking) {
    return null;
  }

  if (!authenticated) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-50 p-4 dark:bg-slate-950">
        <form
          onSubmit={handleSubmit}
          className="w-full max-w-sm space-y-6 rounded-2xl border border-slate-200 bg-white p-8 shadow-sm dark:border-slate-800 dark:bg-slate-900"
        >
          <div className="flex flex-col items-center gap-2">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-indigo-100 dark:bg-indigo-900/30">
              <Lock className="h-6 w-6 text-indigo-500" />
            </div>
            <h1 className="text-xl font-bold text-slate-900 dark:text-slate-100">
              관리자 로그인
            </h1>
            <p className="text-sm text-slate-500">
              관리 페이지에 접근하려면 비밀번호를 입력하세요.
            </p>
          </div>

          <div>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="비밀번호"
              autoFocus
              className="w-full rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
            />
          </div>

          {error && (
            <p className="text-center text-sm font-medium text-red-500">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading || !password}
            className="w-full rounded-lg bg-indigo-600 px-4 py-3 text-sm font-bold text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
          >
            {loading ? "확인 중..." : "로그인"}
          </button>
        </form>
      </main>
    );
  }

  return <>{children}</>;
}
