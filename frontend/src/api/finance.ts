import client from "./client";
export const financeApi = {
 summary: async()=> (await client.get("/finance/summary")).data,
 accounts: async()=> (await client.get("/finance/accounts")).data,
 createAccount: async(data:any)=> (await client.post("/finance/accounts",data)).data,
 transactions: async(params?:any)=> (await client.get("/finance/transactions",{params})).data,
 createTransaction: async(data:any)=> (await client.post("/finance/transactions",data)).data,
 income: async()=> (await client.get("/finance/income")).data,
 createIncome: async(data:any)=> (await client.post("/finance/income",data)).data,
 expenses: async()=> (await client.get("/finance/expenses")).data,
 createExpense: async(data:any)=> (await client.post("/finance/expenses",data)).data,
 budget: async()=> (await client.get("/finance/budget")).data,
 goals: async()=> (await client.get("/finance/goals")).data,
 bills: async()=> (await client.get("/finance/recurring-items")).data,
 debts: async()=> (await client.get("/finance/debts")).data,
 alerts: async()=> (await client.get("/finance/alerts")).data,
 netWorth: async()=> (await client.get("/finance/net-worth")).data,
 statementReminder: async()=> (await client.get("/finance/statement-reminder")).data,
};
