import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from './api';

describe('API client',()=>{
  beforeEach(()=>{sessionStorage.clear();vi.restoreAllMocks()});
  it('sends the session token and parses a successful response',async()=>{
    sessionStorage.setItem('evs_token','session-token');
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>({ok:true})}));
    await expect(api('/health')).resolves.toEqual({ok:true});
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/health'),expect.objectContaining({headers:expect.objectContaining({Authorization:'Bearer session-token'})}));
  });
  it('surfaces API errors',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,statusText:'Bad Request',json:async()=>({detail:'Invalid input'})}));
    await expect(api('/vehicles')).rejects.toThrow('Invalid input');
  });
});
