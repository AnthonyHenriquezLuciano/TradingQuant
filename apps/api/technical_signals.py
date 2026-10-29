"""Real OHLC technical indicator hypotheses for TradingQuant.

Signals use *completed bars* only. The backtester fills on NEXT bar OPEN.
For every returned array, index i never references a candle after i.
No volume, Level II, synthetic delta or macro data are manufactured here.
A selectable indicator must have implemented calculations and tests.
"""
from __future__ import annotations

import numpy as np
from numba import njit


SUPPORTED = (
    "tech_ema","tech_sma","tech_ma","tech_ma_cruce","tech_dema","tech_tema",
    "tech_hma","tech_kama","tech_alma","tech_lsma","tech_wma","tech_smma",
    "tech_median","tech_ichimoku","tech_rsi","tech_macd","tech_adx",
    "tech_cci","tech_roc","tech_estocastico","tech_williamsr","tech_stochrsi",
    "tech_ao","tech_trix","tech_cmo","tech_bop","tech_ppo",
    "tech_bandas_bollinger","tech_bbpercentb","tech_bbwidth","tech_donchian",
    "tech_keltner","tech_atr","tech_bollinger_squeeze",
    "tech_candledirection","tech_candlevolatility","tech_highlow",
    "tech_candle_body_ratio","tech_inside_bar","tech_outside_bar",
    "tech_gap_atr","tech_market_structure_bias",
    "sit_break_of_structure_bos","sit_fair_value_gap_fvg",
    "sit_inside_bar_breakout","sit_failed_breakout","sit_atr_expansion",
    "sit_adx_trend_regime","sit_compresion_de_volatilidad","sit_freno_de_momentum"
)


@njit(cache=True)
def _roll_extreme(arr,period,maximum=True):
    n=len(arr)
    out=np.full(n,np.nan)
    for i in range(period-1,n):
        value=arr[i-period+1]
        for j in range(i-period+2,i+1):
            if maximum and arr[j]>value:value=arr[j]
            elif not maximum and arr[j]<value:value=arr[j]
        out[i]=value
    return out


@njit(cache=True)
def _kama(x,period):
    n=len(x);out=np.full(n,np.nan)
    if n<=period:return out
    out[period]=np.mean(x[:period+1])
    fast=2/3.
    slow=2/31.
    for i in range(period+1,n):
        direction=abs(x[i]-x[i-period])
        volatility=0.
        for j in range(i-period+1,i+1):
            volatility+=abs(x[j]-x[j-1])
        efficiency=direction/volatility if volatility>0 else 0.
        smooth=(efficiency*(fast-slow)+slow)**2
        out[i]=out[i-1]+smooth*(x[i]-out[i-1])
    return out


@njit(cache=True)
def _cci(typical,period):
    n=len(typical);out=np.full(n,np.nan)
    for i in range(period-1,n):
        total=0.
        for j in range(i-period+1,i+1):total+=typical[j]
        mean=total/period
        deviation=0.
        for j in range(i-period+1,i+1):deviation+=abs(typical[j]-mean)
        out[i]=(typical[i]-mean)/(.015*deviation/period) if deviation>0 else 0.
    return out


@njit(cache=True)
def _wilder(x,period):
    n=len(x);out=np.full(n,np.nan)
    if n<period:return out
    total=0.
    for i in range(period):total+=x[i]
    out[period-1]=total/period
    for i in range(period,n):
        out[i]=(out[i-1]*(period-1)+x[i])/period
    return out


@njit(cache=True)
def _adx_dmi(hi,lo,close,period):
    n=len(close)
    plus=np.zeros(n);minus=np.zeros(n);tr=np.zeros(n)
    for i in range(1,n):
        up=hi[i]-hi[i-1];down=lo[i-1]-lo[i]
        plus[i]=up if up>down and up>0 else 0.
        minus[i]=down if down>up and down>0 else 0.
        tr[i]=max(hi[i]-lo[i],abs(hi[i]-close[i-1]),abs(lo[i]-close[i-1]))
    tr_s=_wilder(tr,period);p_s=_wilder(plus,period);m_s=_wilder(minus,period)
    pd=np.full(n,np.nan);md=np.full(n,np.nan)
    dx=np.zeros(n)
    for i in range(period,n):
        if tr_s[i]<=0:continue
        pd[i]=100*p_s[i]/tr_s[i];md[i]=100*m_s[i]/tr_s[i]
        dx[i]=100*abs(pd[i]-md[i])/(pd[i]+md[i]) if pd[i]+md[i]>0 else 0.
    adx=_wilder(dx,period)
    adx[:min(n,period*2)]=np.nan
    return pd,md,adx


def _sma(x,p):
    n=len(x);out=np.full(n,np.nan)
    if n<p:return out
    sums=np.cumsum(np.concatenate(([0.],np.asarray(x,dtype=np.float64))))
    out[p-1:]=(sums[p:]-sums[:-p])/p
    return out


def _ema(x,p):
    n=len(x);out=np.full(n,np.nan)
    if n<p:return out
    out[p-1]=float(np.mean(x[:p]))
    alpha=2./(p+1)
    for i in range(p,n):
        out[i]=alpha*x[i]+(1-alpha)*out[i-1]
    return out


def _wma(x,p):
    n=len(x);out=np.full(n,np.nan)
    if n<p:return out
    w=np.arange(1,p+1,dtype=float)
    out[p-1:]=np.convolve(x,w[::-1],mode="valid")/w.sum()
    return out


def _sma_std(x,p):
    mean=_sma(x,p)
    squared=_sma(x*x,p)
    return mean,np.sqrt(np.maximum(0.,squared-mean*mean))


def _atr(high,low,close,p):
    tr=np.empty(len(close));tr[0]=high[0]-low[0]
    tr[1:]=np.maximum.reduce((high[1:]-low[1:],
        np.abs(high[1:]-close[:-1]),np.abs(low[1:]-close[:-1])))
    return _wilder(tr,p)


def _rsi(close,p):
    delta=np.diff(close,prepend=close[0])
    avg_gain=_wilder(np.maximum(delta,0.),p)
    avg_loss=_wilder(np.maximum(-delta,0.),p)
    rs=avg_gain/np.where(avg_loss>1e-12,avg_loss,1e-12)
    out=100.-100./(1.+rs)
    out[(avg_gain<1e-12)&(avg_loss<1e-12)]=50.
    return out


def _cross(a,b):
    a=np.asarray(a);b=np.asarray(b)
    valid=(np.isfinite(a)&np.isfinite(b))
    prior=valid[1:]&valid[:-1]
    up=prior&(a[:-1]<=b[:-1])&(a[1:]>b[1:])
    down=prior&(a[:-1]>=b[:-1])&(a[1:]<b[1:])
    out=np.zeros(len(a),dtype=np.int8)
    out[1:][up]=1;out[1:][down]=-1
    return out


def _threshold(x,upper,lower):
    # Two-sided oscillator enters on exiting extreme regions.
    out=np.zeros(len(x),dtype=np.int8)
    valid=np.isfinite(x[1:])&np.isfinite(x[:-1])
    out[1:][valid&(x[:-1]<=lower)&(x[1:]>lower)]=1
    out[1:][valid&(x[:-1]>=upper)&(x[1:]<upper)]=-1
    return out


def _direction_close(close,op):
    return np.sign(close-op).astype(np.int8)


def _warmup(signals,period):
    signals[:min(len(signals),max(40,int(period)*3))]=0
    return signals


def technical_signals(name:str,period:int,op,high,low,close):
    """Returns next-bar-executable LONG/SHORT entry events for a supported id."""
    if name not in SUPPORTED:raise ValueError("Indicador sin motor implementado: "+name)
    op=np.asarray(op,dtype=float);high=np.asarray(high,dtype=float)
    low=np.asarray(low,dtype=float);close=np.asarray(close,dtype=float)
    n=len(close);p=int(period)
    if n<60 or p<2 or p>150:raise ValueError("Periodo de indicador inválido")
    sign=np.zeros(n,dtype=np.int8)
    typ=(high+low+close)/3.
    median=(high+low)/2.
    if name in ("tech_ema","tech_sma","tech_ma","tech_dema","tech_tema",
                "tech_hma","tech_kama","tech_alma","tech_lsma","tech_wma",
                "tech_smma","tech_median","tech_ma_cruce"):
        if name=="tech_ema":line=_ema(close,p)
        elif name in ("tech_sma","tech_ma"):line=_sma(close,p)
        elif name=="tech_dema":
            e1=_ema(close,p);line=2*e1-_ema(np.nan_to_num(e1,nan=close[0]),p)
        elif name=="tech_tema":
            e1=_ema(close,p);e2=_ema(np.nan_to_num(e1,nan=close[0]),p);e3=_ema(np.nan_to_num(e2,nan=close[0]),p)
            line=3*e1-3*e2+e3
        elif name=="tech_hma":
            line=_wma(np.nan_to_num(2*_wma(close,max(2,p//2))-_wma(close,p),nan=close[0]),max(2,int(np.sqrt(p))))
        elif name=="tech_kama":line=_kama(close,p)
        elif name=="tech_alma":
            m=.85*(p-1);sigma=max(1.,p/6)
            w=np.exp(-.5*((np.arange(p)-m)/sigma)**2);w/=w.sum()
            line=np.full(n,np.nan);line[p-1:]=np.convolve(close,w[::-1],mode="valid")
        elif name=="tech_lsma":
            x=np.arange(p);weights=(x-x.mean())/np.sum((x-x.mean())**2)
            line=_sma(close,p)+np.convolve(close,weights[::-1],mode="valid").tolist()[0:0] if False else _sma(close,p)
            regression=np.convolve(close,weights[::-1],mode="valid")
            line[p-1:]+=regression*(p-1-x.mean())
        elif name=="tech_wma":line=_wma(close,p)
        elif name=="tech_smma":line=_wilder(close,p)
        elif name=="tech_median":line=_sma(median,p)
        else:line=_sma(close,p)
        sign=_cross(_sma(close,max(3,p//2)),_sma(close,p*2)) if name=="tech_ma_cruce" else _cross(close,line)
    elif name=="tech_ichimoku":
        fast=( _roll_extreme(high,max(5,p//2),True)+_roll_extreme(low,max(5,p//2),False))/2
        slow=( _roll_extreme(high,p,True)+_roll_extreme(low,p,False))/2
        sign=_cross(fast,slow)
    elif name in ("tech_rsi","tech_cmo"):
        r=_rsi(close,p)
        val=r if name=="tech_rsi" else 2*r-100
        sign=_threshold(val,70 if name=="tech_rsi" else 40,
                              30 if name=="tech_rsi" else -40)
    elif name in ("tech_macd","tech_ppo","tech_trix"):
        if name=="tech_trix":
            e1=_ema(close,p);e2=_ema(np.nan_to_num(e1,nan=close[0]),p)
            e3=_ema(np.nan_to_num(e2,nan=close[0]),p)
            osc=np.full(n,np.nan);osc[1:]=100*(e3[1:]-e3[:-1])/np.maximum(np.abs(e3[:-1]),1e-10)
            sign=_cross(osc,np.zeros(n))
        else:
            fast=_ema(close,max(2,p//2));slow=_ema(close,max(4,p))
            osc=fast-slow
            if name=="tech_ppo":osc=osc/np.where(np.abs(slow)>1e-10,slow,np.nan)*100.
            signal=_ema(np.nan_to_num(osc,nan=0.),max(3,p//4))
            sign=_cross(osc,signal)
    elif name in ("tech_adx","sit_adx_trend_regime"):
        pd,md,adx=_adx_dmi(high,low,close,p)
        sign=_cross(pd,md)
        sign[np.nan_to_num(adx,nan=0.)<20]=0
    elif name=="tech_cci":
        sign=_threshold(_cci(typ,p),100,-100)
    elif name=="tech_roc":
        roc=np.full(n,np.nan);roc[p:]=100*(close[p:]/close[:-p]-1.)
        sign=_cross(roc,np.zeros(n))
    elif name in ("tech_estocastico","tech_williamsr"):
        hh=_roll_extreme(high,p,True);ll=_roll_extreme(low,p,False)
        k=100*(close-ll)/np.where(hh>ll,hh-ll,np.nan)
        if name=="tech_estocastico":
            d=_sma(np.nan_to_num(k,nan=50.),3)
            sign=_cross(k,d)
            sign[(k>80)|(k<20)]=0
        else:
            sign=_threshold(k,80,20)
    elif name=="tech_stochrsi":
        r=_rsi(close,p);rh=_roll_extreme(np.nan_to_num(r,nan=50.),p,True)
        rl=_roll_extreme(np.nan_to_num(r,nan=50.),p,False)
        st=100*(r-rl)/np.where(rh>rl,rh-rl,np.nan)
        sign=_threshold(st,80,20)
    elif name=="tech_ao":
        sign=_cross(_sma(median,5)-_sma(median,34),np.zeros(n))
    elif name=="tech_bop":
        bop=(close-op)/np.maximum(high-low,1e-9)
        sign=_cross(_sma(bop,max(2,p//2)),np.zeros(n))
    elif name in ("tech_bandas_bollinger","tech_bbpercentb","tech_bbwidth","tech_bollinger_squeeze"):
        m,std=_sma_std(close,p)
        upper=m+2*std;lower=m-2*std
        if name=="tech_bandas_bollinger":
            sign=_threshold((close-lower)/np.where(upper>lower,upper-lower,np.nan),1.,0.)
        elif name=="tech_bbpercentb":
            sign=_cross((close-lower)/np.where(upper>lower,upper-lower,np.nan),np.full(n,.5))
        elif name=="tech_bbwidth":
            bw=(upper-lower)/np.where(m!=0,m,np.nan)
            sm=_sma(np.nan_to_num(bw,nan=0.),max(p,10))
            expanded=np.isfinite(sm)&(bw>sm*1.4)&(np.roll(bw,1)<=np.roll(sm,1)*1.4)
            sign[expanded]=_direction_close(close,op)[expanded]
        else:
            compressed=(upper-lower)<1.2*_atr(high,low,close,p)
            sign[2:][compressed[:-2]&(close[2:]>upper[1:-1])]=1
            sign[2:][compressed[:-2]&(close[2:]<lower[1:-1])]=-1
    elif name in ("tech_donchian","tech_highlow","tech_market_structure_bias","sit_break_of_structure_bos"):
        p=2 if name=="tech_highlow" else p
        hh=_roll_extreme(high,p,True);ll=_roll_extreme(low,p,False)
        sign[1:][close[1:]>hh[:-1]]=1
        sign[1:][close[1:]<ll[:-1]]=-1
    elif name=="tech_keltner":
        m=_ema(close,p);atr=_atr(high,low,close,p)
        sign=_threshold((close-m)/np.where(atr>0,atr,np.nan),1.5,-1.5)
    elif name in ("tech_atr","sit_atr_expansion","tech_candlevolatility"):
        atr=_atr(high,low,close,p);avg=_sma(np.nan_to_num(atr,nan=0.),p)
        event=(atr>avg*1.4) if name!="tech_candlevolatility" else (np.abs(close-op)>atr*1.25)
        sign[event]=_direction_close(close,op)[event]
    elif name in ("sit_compresion_de_volatilidad",):
        atr=_atr(high,low,close,p)
        trend=_sma(np.nan_to_num(atr,nan=0.),p)
        compressed=np.isfinite(trend)&(atr<trend*.65)
        hh=_roll_extreme(high,p,True);ll=_roll_extreme(low,p,False)
        sign[1:][compressed[:-1]&(close[1:]>hh[:-1])]=1
        sign[1:][compressed[:-1]&(close[1:]<ll[:-1])]=-1
    elif name in ("tech_candledirection", "tech_candle_body_ratio","tech_outside_bar"):
        if name=="tech_candledirection":
            up=(close[1:]>op[1:])&(close[:-1]<op[:-1])
            dn=(close[1:]<op[1:])&(close[:-1]>op[:-1])
            sign[1:][up]=1;sign[1:][dn]=-1
        elif name=="tech_candle_body_ratio":
            body=np.abs(close-op)/np.maximum(high-low,1e-9)
            sign[body>.75]=_direction_close(close,op)[body>.75]
        else:
            outside=(high[1:]>high[:-1])&(low[1:]<low[:-1])
            sign[1:][outside]=_direction_close(close,op)[1:][outside]
    elif name in ("tech_inside_bar","sit_inside_bar_breakout"):
        inside=(high[1:-1]<high[:-2])&(low[1:-1]>low[:-2])
        sign[2:][inside&(close[2:]>high[1:-1])]=1
        sign[2:][inside&(close[2:]<low[1:-1])]=-1
    elif name=="tech_gap_atr":
        atr=_atr(high,low,close,p)
        gap=(op[1:]-close[:-1])/np.maximum(atr[:-1],1e-10)
        sign[1:][gap>.5]=1;sign[1:][gap<-.5]=-1
    elif name=="sit_fair_value_gap_fvg":
        sign[2:][low[2:]>high[:-2]]=1
        sign[2:][high[2:]<low[:-2]]=-1
    elif name=="sit_failed_breakout":
        hh=_roll_extreme(high,p,True);ll=_roll_extreme(low,p,False)
        sign[1:][(high[1:]>hh[:-1])&(close[1:]<hh[:-1])]=-1
        sign[1:][(low[1:]<ll[:-1])&(close[1:]>ll[:-1])]=1
    elif name=="sit_freno_de_momentum":
        r=_rsi(close,p)
        sign=_threshold(r,75,25)
    else:
        raise ValueError("El indicador no dispone de fórmula validada: "+name)
    return _warmup(sign,p)
