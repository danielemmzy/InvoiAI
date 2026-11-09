"use client";

import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2, Zap } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import MotionMark from "@/components/ui/MotionMark";

const E164 = /^\+[1-9]\d{7,14}$/;

const schema = z.object({
  firstName: z
    .string()
    .trim()
    .min(1, "First name is required")
    .max(100, "Use 100 characters or fewer"),
  lastName: z
    .string()
    .trim()
    .min(1, "Last name is required")
    .max(100, "Use 100 characters or fewer"),
  email: z.string().email("Enter a valid email"),
  password: z.string().min(8, "Password must be at least 8 characters"),
  mobile: z
    .string()
    .trim()
    .refine(
      (value) =>
        !value || E164.test(value.replace(/[\s-]/g, "")),
      "Include a country code, for example +447700900123",
    ),
});

type FormData = z.infer<typeof schema>;

export default function SignupPage() {
  const { signup, isSigningUp } = useAuth();
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { mobile: "" },
  });

  return (
    <div className="auth-layout">
      <aside className="auth-panel">
        <div className="auth-team-photo" role="img" aria-label="A finance team collaborating in a bright office" />
        <div className="auth-photo-wash" />
        <div className="auth-panel-logo">
          <div className="auth-panel-icon"><Zap size={16} /></div>
          <span className="auth-panel-logo-text">invoi<span>ai</span></span>
        </div>
        <div className="auth-story">
          <p className="auth-panel-quote">Give every invoice a clear path forward.</p>
          <ul className="feature-list" aria-label="What you can do with InvoiAI">
            {["Upload any invoice, any format", "Review structured document capture", "Set up a focused AP workspace"].map((item) => (
              <li key={item} className="feature-item">
                <span className="feature-check" aria-hidden="true">✓</span>
                <span className="feature-text">{item}</span>
              </li>
            ))}
          </ul>
          <div className="auth-lottie-frame" aria-hidden="true">
            <MotionMark />
          </div>
        </div>
        <p className="auth-panel-desc">Start with the controls your team needs.</p>
      </aside>

      <main className="auth-form-panel">
        <div className="auth-form-inner">
          <div className="auth-mobile-motion" aria-hidden="true">
            <MotionMark />
          </div>
          <h1 className="auth-title">Create your account</h1>
          <p className="auth-subtitle">Already have an account? <Link href="/login">Sign in</Link></p>

          <form
            onSubmit={handleSubmit((data) =>
              signup({
                firstName: data.firstName,
                lastName: data.lastName,
                email: data.email,
                password: data.password,
                mobile: data.mobile,
              })
            )}
          >
            <div className="form-name-grid">
              <div className="form-group">
                <label className="form-label" htmlFor="signup-first-name">First name</label>
                <input
                  id="signup-first-name"
                  {...register("firstName")}
                  type="text"
                  autoComplete="given-name"
                  placeholder="Ada"
                  className={`form-input${errors.firstName ? " error" : ""}`}
                  aria-invalid={Boolean(errors.firstName)}
                />
                {errors.firstName && <p className="form-error">{errors.firstName.message}</p>}
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="signup-last-name">Last name</label>
                <input
                  id="signup-last-name"
                  {...register("lastName")}
                  type="text"
                  autoComplete="family-name"
                  placeholder="Lovelace"
                  className={`form-input${errors.lastName ? " error" : ""}`}
                  aria-invalid={Boolean(errors.lastName)}
                />
                {errors.lastName && <p className="form-error">{errors.lastName.message}</p>}
              </div>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="signup-email">Email address</label>
              <input id="signup-email" {...register("email")} type="email" autoComplete="email" placeholder="you@company.com" className={`form-input${errors.email ? " error" : ""}`} aria-invalid={Boolean(errors.email)} />
              {errors.email && <p className="form-error">{errors.email.message}</p>}
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="signup-password">Password</label>
              <input id="signup-password" {...register("password")} type="password" autoComplete="new-password" placeholder="At least 8 characters" className={`form-input${errors.password ? " error" : ""}`} aria-invalid={Boolean(errors.password)} />
              {errors.password && <p className="form-error">{errors.password.message}</p>}
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="signup-mobile">
                Mobile number <span className="form-optional">Optional</span>
              </label>
              <input
                id="signup-mobile"
                {...register("mobile")}
                type="tel"
                autoComplete="tel"
                inputMode="tel"
                placeholder="+44 7700 900123"
                className={`form-input${errors.mobile ? " error" : ""}`}
                aria-invalid={Boolean(errors.mobile)}
                aria-describedby="signup-mobile-hint"
              />
              <p className="form-hint" id="signup-mobile-hint">
                Include the country code. We verify your email, not your
                phone number.
              </p>
              {errors.mobile && <p className="form-error">{errors.mobile.message}</p>}
            </div>

            <button type="submit" disabled={isSigningUp} className="form-submit">
              {isSigningUp ? <><Loader2 size={15} className="animate-spin" /> Creating account...</> : "Create account"}
            </button>
            <p className="form-note">By signing up, you agree to the Terms of Service and Privacy Policy.</p>
          </form>
        </div>
      </main>
    </div>
  );
}
