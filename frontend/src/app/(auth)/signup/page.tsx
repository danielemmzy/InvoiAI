"use client";
// Signup page — /signup

import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2, Zap } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(8, "Password must be at least 8 characters"),
});
type FormData = z.infer<typeof schema>;

export default function SignupPage() {
  const { signup, isSigningUp } = useAuth();
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({ resolver: zodResolver(schema) });
  const onSubmit = (data: FormData) => signup(data);

  return (
    <div className="auth-layout">
      {/* Left panel */}
      <div className="auth-panel">
        <div className="auth-panel-logo">
          <div className="auth-panel-icon"><Zap size={16} color="#C8922A" /></div>
          <span className="auth-panel-logo-text serif">Invoi<span>AI</span></span>
        </div>
        <div>
          <p className="serif" style={{ fontSize: 22, fontWeight: 500, color: "#FFFFFF", lineHeight: 1.5, marginBottom: 24 }}>
            Join thousands of accountants saving 4+ hours per week.
          </p>
          <div className="feature-list">
            {[
              "Upload any invoice, any format",
              "20 industry-specific extraction modes",
              "Excel, CSV and Google Sheets export",
              "10 free documents to start",
            ].map((item) => (
              <div key={item} className="feature-item">
                <div className="feature-check">✓</div>
                <span className="feature-text">{item}</span>
              </div>
            ))}
          </div>
        </div>
        <p style={{ fontSize: 12, color: "#555" }}>No credit card required · Cancel anytime</p>
      </div>

      {/* Right panel */}
      <div className="auth-form-panel">
        <div className="auth-form-inner">
          <h1 className="auth-title serif">Create your account</h1>
          <p className="auth-subtitle">
            Already have an account?{" "}
            <Link href="/login">Sign in</Link>
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
                placeholder="At least 8 characters"
                className={`form-input${errors.password ? " error" : ""}`}
              />
              {errors.password && <p className="form-error">{errors.password.message}</p>}
            </div>

            <button type="submit" disabled={isSigningUp} className="form-submit">
              {isSigningUp ? <><Loader2 size={15} className="animate-spin" /> Creating account...</> : "Create account — it's free →"}
            </button>
            <p className="form-note">By signing up you agree to our Terms of Service.</p>
          </form>
        </div>
      </div>
    </div>
  );
}