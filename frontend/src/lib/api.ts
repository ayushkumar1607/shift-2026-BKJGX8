const BASE=import.meta.env.VITE_API_URL||"/api/v1";
export function token(){return sessionStorage.getItem("evs_token")||""}
export async function api<T=any>(path:string,opts:RequestInit={}):Promise<T>{const res=await fetch(BASE+path,{...opts,headers:{"Content-Type":"application/json",...(token()?{Authorization:`Bearer ${token()}`}:{}) ,...(opts.headers||{})}});const data=await res.json().catch(()=>({detail:res.statusText}));if(!res.ok)throw new Error(data.detail||"Request failed");return data}
