"use client";
import Link from "next/link";
import { useState } from "react";
import { CheckCircle2, Mail, Loader2 } from "lucide-react";
import { authApi } from "@/api/auth";
import { getErrorMessage } from "@/api/client";
export default function VerifyEmailPage(){
 const [email,setEmail]=useState("");const [busy,setBusy]=useState(false);const [message,setMessage]=useState("");
 async function resend(){setBusy(true);try{const r=await authApi.resendVerification(email);setMessage(r.message)}catch(e){setMessage(getErrorMessage(e,"Please try again shortly."))}finally{setBusy(false)}}
 return <div className="auth-shell"><div className="auth-art"><div className="auth-panel-brand">Invoi<span>AI</span></div><div className="ledger"><CheckCircle2 size={22} color="#6FC29A"/><h2 style={{fontFamily:"var(--display)",fontSize:30,margin:"16px 0 8px"}}>One last step.</h2><p style={{color:"#aaa",lineHeight:1.7,fontSize:14}}>Verify your email before entering your finance workspace.</p></div></div><main className="auth-form-wrap"><section className="auth-form"><div style={{width:54,height:54,borderRadius:16,display:"grid",placeItems:"center",background:"#F2E6CF",marginBottom:22}}><Mail size={25} color="#B98532"/></div><h1 className="auth-title">Check your email</h1><p className="auth-subtitle">We sent a verification link to the email you used to create InvoiAI.</p><div className="auth-field"><label htmlFor="email">Didn't receive it? Enter your email</label><input id="email" type="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="you@company.com"/></div>{message&&<div className="soft-notice">{message}</div>}<button className="auth-submit" onClick={resend} disabled={busy||!email}>{busy?<><Loader2 size={16} className="animate-spin"/>Sending…</>:"Resend verification email"}</button><p className="auth-foot"><Link href="/login">Return to sign in</Link></p></section></main></div>
}