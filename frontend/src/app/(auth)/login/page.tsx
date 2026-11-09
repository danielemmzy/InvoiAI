"use client";
// Login page — /login

import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2, ShieldCheck, Zap } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import MotionMark from "@/components/ui/MotionMark";
import GoogleSignInButton from "@/components/auth/GoogleSignInButton";

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
        <div className="auth-team-photo" role="img" aria-label="A finance team collaborating in a bright office" />
        <div className="auth-photo-wash" />
        <div className="auth-panel-logo">
          <div className="auth-panel-icon"><Zap size={16} color="#C8922A" /></div>
          <span className="auth-panel-logo-text serif">Invoi<span>AI</span></span>
        </div>
        <div className="auth-story">
          <p className="auth-panel-quote serif">Every decision has a source. Every source has an owner.</p>
          <p className="auth-panel-author">Return to the workspace where every payable has a clear next step.</p>
          <div className="auth-lottie-frame" aria-hidden="true"><MotionMark /></div>
        </div>
        <div className="auth-panel-user">
          <div className="auth-panel-avatar"><ShieldCheck size={14} /></div>
          <div>
            <div className="auth-panel-name">Control room access</div>
            <div className="auth-panel-desc">Secure sign in</div>
          </div>
        </div>
      </div>

      {/* Right panel */}
      <div className="auth-form-panel">
        <div className="auth-form-inner">
          <div className="auth-mobile-motion" aria-hidden="true"><MotionMark /></div>
          <h1 className="auth-title serif">Welcome back</h1>
          <p className="auth-subtitle">
            Don&apos;t have an account?{" "}
            <Link href="/signup">Sign up free</Link>
          </p>

          <GoogleSignInButton />
          <div className="auth-subtitle" style={{ textAlign: "center", margin: "18px 0" }}>or sign in with email</div>

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
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <label className="form-label" htmlFor="login-password">Password</label>
                <Link href="/forgot-password" className="form-hint">Forgot password?</Link>
              </div>
              <input
                id="login-password"
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
