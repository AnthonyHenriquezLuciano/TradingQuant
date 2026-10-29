"""Walk-forward diagnostics and synthetic OHLC stress scenarios.

No OOS data are used to select initial candidates; WF folds are chronological.
Synthetic universes are generated strictly from the IS market window and then
signals must be recomputed on those universes by the calling engine.

The Gaussian HMM is an exploratory fitted regime descriptor, NOT a true
identification of hidden economic states. Validation is numerical, not audited.
"""
from __future__ import annotations
import math
import numpy as np
from research_validation import validate_walkforward,validate_multiverse,realized_quality
from engine import summarize

def walkforward_bounds(start:int,end:int,settings:dict):
    c=validate_walkforward(settings)
    if end-start < max(120,c["rolling_windows"]*35):
        raise ValueError("Periodo OOS insuficiente para las ventanas walk-forward.")
    w=max(35,(end-start)//c["test_fraction"])
    n=min(c["rolling_windows"],max(1,(end-start)//w))
    windows=[]
    for j in range(n):
        a=start+j*w
        b=end if j==n-1 else min(end,a+w)
        if b>a:windows.append((a,b))
    return windows


def walkforward_report(
    windows, results, is_return_per_day, cfg, risk_pct, sizing, deposit, daily_dd, total_dd
):
    """results is a sequence of (R, exit_days, observed_bar_days) for each fold."""
    c=validate_walkforward(cfg)
    folds=[]
    for (start,end),(r,dates,obs) in zip(windows,results):
        metrics=summarize(np.asarray(r),np.asarray(dates),risk_pct,daily_dd,total_dd,sizing,deposit)
        quality=realized_quality(r,dates,obs,risk_pct,sizing,metrics)
        oos_daily=metrics["net_return_pct"]/max(1,quality["observed_days"])
        wfe=oos_daily/is_return_per_day if is_return_per_day>0 else 0.
        good=(wfe>=c["min_efficiency"] and quality["sharpe"]>=c["min_oos_sharpe"] and
              quality["trades"]>0 and metrics["net_return_pct"]>0)
        folds.append({
            "start_bar":start,"end_bar":end,"trades":metrics["trades"],
            "sharpe":quality["sharpe"],"wfe":round(float(np.clip(wfe,-100,100)),4),
            "return_pct":metrics["net_return_pct"],"pass":bool(good)
        })
    passed=100.*sum(int(f["pass"]) for f in folds)/len(folds) if folds else 0.
    efficiency=float(np.median([f["wfe"] for f in folds])) if folds else 0.
    return {"enabled":True,"mode":c["mode"],"windows":folds,"tested_windows":len(folds),
            "pass_rate_pct":round(passed,2),"median_wfe":round(efficiency,4),
            "eligible":bool(folds and passed>=c["min_pass_rate_pct"]),
            "method":"realized_OOS_folds_no_overlap",}


def _normalize(x):
    p=np.asarray(x,dtype=float)
    p=p-np.max(p)
    z=np.exp(np.maximum(p,-500.))
    return z/max(1e-30,float(z.sum()))


def gaussian_hmm_regimes(log_returns:np.ndarray,n_states:int=3,iterations:int=9):
    """Simple scaled Baum–Welch Gaussian HMM: temporal transitions are fitted.

    Hidden states may overlap or collapse on small datasets. Use only for
    regime summaries and stress diagnostics, never for future trade signals.
    """
    x=np.asarray(log_returns,dtype=float)
    x=x[np.isfinite(x)]
    if n_states==1 or len(x)<max(100,30*n_states):
        return {"regime_weights":[1.],"means":[float(np.mean(x)) if len(x) else 0.],
                "volatilities":[float(np.std(x)) if len(x) else 0.],"fitted":False}
    T=len(x);k=n_states
    std=max(float(np.std(x)),1e-8)
    means=np.quantile(x,np.linspace(.2,.8,k))
    vars_=np.full(k,std**2)
    trans=np.eye(k)*.86+np.ones((k,k))*.14/k
    pi=np.ones(k)/k
    gamma=np.empty((T,k))
    for _ in range(iterations):
        z=np.maximum(vars_,std**2*.01)
        emit=np.exp(-.5*(x[:,None]-means[None,:])**2/z[None,:])/np.sqrt(2*np.pi*z[None,:])
        emit=np.maximum(emit,1e-160)
        alpha=np.empty((T,k));scale=np.empty(T)
        alpha[0]=pi*emit[0];scale[0]=max(alpha[0].sum(),1e-160);alpha[0]/=scale[0]
        for t in range(1,T):
            alpha[t]=(alpha[t-1]@trans)*emit[t]
            scale[t]=max(alpha[t].sum(),1e-160);alpha[t]/=scale[t]
        beta=np.ones((T,k))
        for t in range(T-2,-1,-1):
            beta[t]=trans@(emit[t+1]*beta[t+1])
            beta[t]/=max(scale[t+1],1e-160)
        gamma=alpha*beta
        gamma/=np.maximum(gamma.sum(axis=1,keepdims=True),1e-160)
        weights=gamma.sum(axis=0)
        means=(gamma*x[:,None]).sum(axis=0)/np.maximum(weights,1e-160)
        vars_=(gamma*(x[:,None]-means)**2).sum(axis=0)/np.maximum(weights,1e-160)
        vars_=np.maximum(vars_,std**2*.01)
        newtrans=np.zeros((k,k))
        for t in range(T-1):
            xi=alpha[t,:,None]*trans*(emit[t+1]*beta[t+1])[None,:]
            newtrans+=xi/max(xi.sum(),1e-160)
        trans=newtrans/np.maximum(newtrans.sum(axis=1,keepdims=True),1e-160)
        pi=gamma[0]
    order=np.argsort(np.sqrt(vars_))
    return {"regime_weights":[round(float(x),4) for x in (gamma.mean(axis=0)[order])],
            "means":[round(float(v),8) for v in means[order]],
            "volatilities":[round(float(v),8) for v in np.sqrt(vars_[order])],
            "fitted":True,"method":"gaussian_em_hmm"}


def synthetic_ohlc(op,hi,lo,cl,rng:np.random.Generator,mix:str,universe_number:int):
    """Create continuous, strictly positive synthetic price candles."""
    op=np.asarray(op,dtype=float);hi=np.asarray(hi,dtype=float)
    lo=np.asarray(lo,dtype=float);cl=np.asarray(cl,dtype=float)
    n=len(cl)
    if n<100 or np.any(op<=0) or np.any(cl<=0) or np.any(lo<=0):
        raise ValueError("No hay suficientes precios OHLC positivos para sintetizar.")
    returns=np.diff(np.log(cl))
    if mix=="conservative":
        weights=(.5,.5,0.)
    elif mix=="stress":
        weights=(.2,.4,.4)
    else:
        weights=(.4,.4,.2)
    choice=rng.choice(3,p=weights)
    block=(28 if choice==0 else 5 if choice==1 else 3)
    sampled=np.empty(n-1)
    sources=np.empty(n-1,dtype=np.int32)
    pos=0
    while pos<n-1:
        take=min(n-1-pos,block)
        src=int(rng.integers(0,max(1,len(returns)-take+1)))
        sampled[pos:pos+take]=returns[src:src+take]
        sources[pos:pos+take]=np.arange(src,src+take,dtype=np.int32)
        pos+=take
    if choice==2:
        tail=float(np.quantile(np.abs(returns),.995))
        jumps=rng.random(n-1)<.012
        sampled[jumps]+=rng.choice([-1.,1.],size=jumps.sum())*max(tail,.00001)*rng.uniform(1.5,2.5,size=jumps.sum())
    sampled=np.clip(sampled,-.25,.25)
    out_open=np.empty(n);out_high=np.empty(n);out_low=np.empty(n);out_close=np.empty(n)
    out_close[0]=cl[0];out_open[0]=op[0];out_high[0]=hi[0];out_low[0]=lo[0]
    # Candle OHLC is generated from a continuous path: next open = prev close.
    for j in range(1,n):
        k=int(sources[j-1]+1)
        out_open[j]=out_close[j-1]
        out_close[j]=max(1e-10,out_open[j]*math.exp(float(sampled[j-1])))
        wick_up=max(0.,float(hi[k])-max(float(op[k]),float(cl[k])))/float(cl[k])
        wick_dn=max(0.,min(float(op[k]),float(cl[k]))-float(lo[k]))/float(cl[k])
        out_high[j]=max(out_open[j],out_close[j])*(1.+wick_up)
        out_low[j]=max(1e-10,min(out_open[j],out_close[j])*(1.-min(.8,wick_dn)))
    return out_open,out_high,out_low,out_close


def stylized_fact_score(real_close,synthetic_close):
    a=np.diff(np.log(np.asarray(real_close,dtype=float)))
    b=np.diff(np.log(np.asarray(synthetic_close,dtype=float)))
    if min(len(a),len(b))<50:return 0.
    # Robust tests: volatility, empirical tail, clustering of absolute returns.
    sigma_ratio=np.std(b)/max(1e-12,float(np.std(a)))
    tails_ratio=np.quantile(np.abs(b),.99)/max(1e-12,float(np.quantile(np.abs(a),.99)))
    def cluster(x):
        y=np.abs(x)
        return float(np.corrcoef(y[1:],y[:-1])[0,1]) if np.std(y)>1e-12 else 0.
    auto_distance=abs(cluster(b)-cluster(a))
    return float(np.clip(100*(1.-.45*abs(np.log(max(sigma_ratio,1e-10)))-
                        .35*abs(np.log(max(tails_ratio,1e-10)))-.2*auto_distance),0,100))


def multiverse_report(scenarios, config, hidden_regimes):
    """scenario items contain (expectancy_R, realized_dd_pct, style_score)."""
    c=validate_multiverse(config)
    arr=np.asarray(scenarios,dtype=float)
    if arr.size==0:
        return {"enabled":True,"score":0.,"eligible":False,
                "reason":"Sin simulaciones completas", "universes":0}
    survived=(arr[:,0]>0)&(arr[:,1]<=c["max_robust_drawdown_pct"])
    robust=100.*survived.mean()
    style=100.*np.mean(arr[:,2]>=60.)
    score=.8*robust+.2*style if c["validate_fat_tails"] else robust
    p95=float(np.percentile(arr[:,1],95))
    return {"enabled":True,"universes":len(arr),"survival_pct":round(float(robust),2),
            "stylized_pass_pct":round(float(style),2),"median_expectancy_r":round(float(np.median(arr[:,0])),4),
            "p95_drawdown_pct":round(p95,2),"score":round(float(score),2),
            "eligible":bool(score>=c["min_score"] and p95<=c["max_robust_drawdown_pct"]),
            "hidden_regimes":hidden_regimes,
            "method":"IS_only_block_bootstrap_recomputed_signals_HMM_regimes",
            "disclaimer":"Simulaciones hipotéticas, no escenarios de mercado garantizados."}
