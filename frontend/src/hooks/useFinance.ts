"use client";

import {useMutation, useQuery, useQueryClient} from "@tanstack/react-query";
import {financeApi} from "@/api/finance";
import {useAppStore} from "@/store/useAppStore";

export function useFinance(){
  const ws=useAppStore(s=>s.activeWorkspace?.id);
  const qc=useQueryClient();
  const key=["finance",ws];
  const enabled=!!ws;
  const summary=useQuery({queryKey:[...key,"summary"],queryFn:financeApi.summary,enabled,staleTime:30_000,gcTime:5*60_000,refetchOnWindowFocus:false});
  const accounts=useQuery({queryKey:[...key,"accounts"],queryFn:financeApi.accounts,enabled,staleTime:30_000,gcTime:5*60_000,refetchOnWindowFocus:false});
  const tx=useQuery({queryKey:[...key,"transactions"],queryFn:()=>financeApi.transactions(),enabled,staleTime:15_000,gcTime:5*60_000,refetchOnWindowFocus:false});
  const alerts=useQuery({queryKey:[...key,"alerts"],queryFn:financeApi.alerts,enabled,staleTime:20_000,gcTime:5*60_000,refetchOnWindowFocus:false});
  const netWorth=useQuery({queryKey:[...key,"net-worth"],queryFn:financeApi.netWorth,enabled,staleTime:60_000,gcTime:10*60_000,refetchOnWindowFocus:false});
  const statementReminder=useQuery({queryKey:[...key,"statement-reminder"],queryFn:financeApi.statementReminder,enabled,staleTime:60_000,gcTime:10*60_000,refetchInterval:5*60_000,refetchOnWindowFocus:false});
  const invalidate=()=>qc.invalidateQueries({queryKey:key});
  const createTx=useMutation({mutationFn:financeApi.createTransaction,onSuccess:invalidate});
  const createAccount=useMutation({mutationFn:financeApi.createAccount,onSuccess:invalidate});
  const createIncome=useMutation({mutationFn:financeApi.createIncome,onSuccess:invalidate});
  const createExpense=useMutation({mutationFn:financeApi.createExpense,onSuccess:invalidate});
  return {summary,accounts,tx,alerts,netWorth,statementReminder,createTx,createAccount,createIncome,createExpense};
}
