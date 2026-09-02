"use client";

import { useState } from "react";
import { Building2, Check, ChevronDown, Plus, UserRound } from "lucide-react";
import { useWorkspaces, useSwitchWorkspace } from "@/hooks/useWorkspaces";
import { useRouter } from "next/navigation";
import { useAppStore } from "@/store/useAppStore";

export default function WorkspaceSwitcher() {
  const router = useRouter();
  const { data = [], isLoading } = useWorkspaces();
  const active = useAppStore((s) => s.activeWorkspace);
  const switchWorkspace = useSwitchWorkspace();
  const [open, setOpen] = useState(false);

  return <div className="workspace-switcher">
    <button className="workspace-trigger" onClick={() => setOpen((v) => !v)} aria-expanded={open} disabled={isLoading}>
      <span className={`workspace-mini-icon ${active?.type === "personal" ? "personal" : "business"}`}>{active?.type === "personal" ? <UserRound size={15}/> : <Building2 size={15}/>}</span>
      <span className="workspace-trigger-copy"><strong>{active?.name || "Workspace"}</strong><small>{active?.type === "personal" ? "Personal" : "Business"}</small></span>
      <ChevronDown size={15}/>
    </button>
    {open && <>
      <button className="workspace-backdrop" aria-label="Close workspace menu" onClick={() => setOpen(false)}/>
      <div className="workspace-menu">
        <div className="workspace-menu-title">Your workspaces</div>
        {data.map((workspace) => <button key={workspace.id} className="workspace-menu-item" onClick={() => { setOpen(false); switchWorkspace(workspace); }}>
          <span className={`workspace-mini-icon ${workspace.type}`}>{workspace.type === "personal" ? <UserRound size={15}/> : <Building2 size={15}/>}</span>
          <span><strong>{workspace.name}</strong><small>{workspace.type === "personal" ? "Personal" : "Business"} · {workspace.role}</small></span>
          {active?.id === workspace.id && <Check size={16}/>} 
        </button>)}
        <div className="workspace-menu-divider"/>
        <button className="workspace-create-link" onClick={() => { setOpen(false); router.push("/workspace?create=business"); }}><Plus size={15}/> Create business workspace</button>
        {!data.some((w) => w.type === "personal") && <button className="workspace-create-link" onClick={() => { setOpen(false); router.push("/workspace?create=personal"); }}><Plus size={15}/> Create personal workspace</button>}
      </div>
    </>}
  </div>;
}
