"use client";
// Login page — /login

import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2, Zap } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});
type FormData = z.infer<typeof schema>;

export default function LoginPage() {
  const { login, isLoggingIn } = useAuth();
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({ resolver: zodResolver(schema) });
  const onSubmit = (data: FormData) => login(data);

  return (
    <div className="auth-layout">
      {/* Left panel */}
      <div className="auth-panel">
        <div className="auth-panel-logo">
          <div className="auth-panel-icon"><Zap size={16} color="#C8922A" /></div>
          <span className="auth-panel-logo-text serif">Invoi<span>AI</span></span>
        </div>
        <div>
          <p className="auth-panel-quote serif">
            "InvoiAI cut our invoice processing time from 4 hours to 8 minutes."
          </p>
          <p className="auth-panel-author">Chidi O. · Finance Manager, Lagos</p>
        </div>
        <div className="auth-panel-user">
          <div className="auth-panel-avatar">C</div>
          <div>
            <div className="auth-panel-name">Chidi Okonkwo</div>
            <div className="auth-panel-desc">Pro plan · 480 docs this month</div>
          </div>
        </div>
      </div>

      {/* Right panel */}
      <div className="auth-form-panel">
        <div className="auth-form-inner">
          <h1 className="auth-title serif">Welcome back</h1>
          <p className="auth-subtitle">
            Don&apos;t have an account?{" "}
            <Link href="/signup">Sign up free</Link>
          </p>

          <form onSubmit={handleSubmit(onSubmit)}>
            <div className="form-group">
              <label className="form-label">Email address</label>
              <input
                {...register("email")}
                type="email"
                placeholder="you@company.com"
                className={`form-input${errors.email ? " error" : ""}`}
              />
              {errors.email && <p className="form-error">{errors.email.message}</p>}
            </div>

            <div className="form-group">
              <label className="form-label">Password</label>
              <input
                {...register("password")}
                type="password"
                placeholder="••••••••"
                className={`form-input${errors.password ? " error" : ""}`}
              />
              {errors.password && <p className="form-error">{errors.password.message}</p>}
            </div>

            <button type="submit" disabled={isLoggingIn} className="form-submit">
              {isLoggingIn ? <><Loader2 size={15} className="animate-spin" /> Signing in...</> : "Sign in →"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}