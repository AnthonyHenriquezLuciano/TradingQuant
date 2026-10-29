"""Numba OHLC simulator for selected advanced entry and position modifiers.

Conservative conventions:
- Signals known at preceding close; stop/limit placed at next bar and expire.
- Pending order fills use favorable limit or adverse stop gaps.
- Newly filled *pending* entries are not stopped/targeted until next bar.
- Existing-position SL/TP checked before adding a DCA or pyramid leg.
- Maximum planned stop-loss budget is divided among ALL reserved legs.
- BE/trailing update at bar CLOSE for the following bar; stop never loosens.
- A trade with added legs counts as ONE trade. No margin or tick fills.
"""
from __future__ import annotations
import numpy as np
from numba import njit

@njit(cache=True)
def _distance(unit, val, a, risk, price):
    if unit == 0:
        return val*a
    if unit == 1:
        return val*risk
    return price*val/100.


@njit(cache=True)
def simulate_advanced_orders(
    signals,op,hi,lo,cl,atr,days,start,end,
    exit_code,sl_factor,tp_factor,cost_bps,direction,modeling,
    risk_pct,initial_deposit,fixed_sizing,
    capital_be,capital_be_r,capital_trail,capital_trail_atr,max_hold,
    max_day,cooldown,daily_dd,total_dd,profit_stop,
    allowed,forced,weeks,months,max_gains,max_losses,max_wins,max_losses_streak,
    entry_mode,
    stop_lookback,order_expiry,limit_offset,
    rr_enabled,fixed_rr,risk_enabled,risk_mode,risk_multiplier,risk_max_levels,risk_reset_on_win,
    be_enabled,be_unit,be_trigger,be_offset,
    trail_enabled,trail_activation_unit,trail_activation,trail_distance_unit,trail_distance,
    dca_enabled,dca_levels,dca_size_multiplier,dca_spacing_unit,dca_spacing,
    pyramid_enabled,pyramid_levels,pyramid_size_multiplier,pyramid_spacing_unit,pyramid_spacing,
    tp_from_average
):
    n=end-start
    outcome=np.empty(n,np.float64)
    exit_day=np.empty(n,np.int32)
    count=0
    equity=1.
    day_open=1.
    week_open=1.
    month_open=1.
    last_day=days[max(0,start)]
    last_week=weeks[max(0,start)]
    last_month=months[max(0,start)]
    deals_today=0
    wins=0
    losses=0
    risk_level=0
    frozen=False
    last_exit=-100000
    pending_side=0
    pending_level=0.
    pending_created=0
    side=0
    entry_bar=0
    total_qty=0.
    sum_entry_qty=0.
    initial_entry=0.
    initial_dist=0.
    avg=0.
    stop=0.
    take=0.
    initial_take_dist=0.
    original_nominal_risk=0.
    reserved_budget=0.
    total_weights=1.
    dca_count=1
    pyramid_count=1
    dca_last=0.
    pyramid_last=0.
    initial_atr=0.
    trailing_started=False

    for i in range(max(41,start),end):
        pending_stop_hit=False
        if days[i]!=last_day:
            last_day=days[i]
            day_open=equity
            deals_today=0
            wins=0
            losses=0
            frozen=False
        if weeks[i]!=last_week:
            last_week=weeks[i]
            week_open=equity
        if months[i]!=last_month:
            last_month=months[i]
            month_open=equity

        if side==0:
            if pending_side!=0 and (i-pending_created>=order_expiry or not allowed[i] or forced[i]):
                pending_side=0
            pass_guard=True
            if not allowed[i] or forced[i] or frozen or equity<=0 or equity<1.-total_dd/100.:
                pass_guard=False
            dp=(equity/day_open-1.)*100. if day_open>0 else -100.
            wp=(equity/week_open-1.)*100. if week_open>0 else -100.
            mp=(equity/month_open-1.)*100. if month_open>0 else -100.
            ap=(equity-1.)*100.
            if dp<=-daily_dd or (profit_stop>0 and dp>=profit_stop):
                pass_guard=False
            if max_day>0 and deals_today>=max_day or i<=last_exit+cooldown:
                pass_guard=False
            if (max_gains[0]>0 and dp>=max_gains[0] or max_gains[1]>0 and wp>=max_gains[1]
                or max_gains[2]>0 and mp>=max_gains[2] or max_gains[3]>0 and ap>=max_gains[3]
                or max_losses[0]>0 and dp<=-max_losses[0] or max_losses[1]>0 and wp<=-max_losses[1]
                or max_losses[2]>0 and mp<=-max_losses[2] or max_losses[3]>0 and ap<=-max_losses[3]):
                pass_guard=False
            if not pass_guard:
                pending_side=0
                continue
            if pending_side==0:
                sig=signals[i-1]
                if sig==0 or direction==1 and sig<0 or direction==-1 and sig>0:
                    continue
                pending_side=sig
                pending_created=i
                if entry_mode==1:
                    startlb=max(0,i-stop_lookback)
                    pending_level=hi[startlb]
                    if sig<0:
                        pending_level=lo[startlb]
                    for j in range(startlb+1,i):
                        if sig>0 and hi[j]>pending_level:
                            pending_level=hi[j]
                        if sig<0 and lo[j]<pending_level:
                            pending_level=lo[j]
                elif entry_mode==2:
                    pending_level=cl[i-1]-sig*atr[i-1]*limit_offset
                else:
                    pending_level=op[i]

            px=np.nan
            if entry_mode==0:
                px=op[i]
            elif entry_mode==1:
                if pending_side>0 and hi[i]>=pending_level:
                    px=max(op[i],pending_level)
                elif pending_side<0 and lo[i]<=pending_level:
                    px=min(op[i],pending_level)
            else:
                if pending_side>0 and lo[i]<=pending_level:
                    px=min(op[i],pending_level)
                elif pending_side<0 and hi[i]>=pending_level:
                    px=max(op[i],pending_level)
            if not np.isfinite(px):
                continue

            dist=px*sl_factor/100. if exit_code==2 else atr[i-1]*sl_factor
            if not np.isfinite(dist) or dist<=0 or px<=0:
                pending_side=0
                continue
            side=pending_side
            pending_side=0
            entry_bar=i
            initial_entry=px
            initial_atr=atr[i-1]
            avg=px
            initial_dist=dist
            stop=px-side*dist
            initial_take_dist=(fixed_rr*dist if rr_enabled else
                               tp_factor*dist if exit_code in (0,2) else
                               atr[i-1]*tp_factor)
            take=px+side*initial_take_dist
            original_nominal_risk=(1. if fixed_sizing else equity)*risk_pct/100.
            factor=(risk_multiplier**risk_level) if risk_enabled else 1.
            factor=min(factor,2./max(.00001,risk_pct))
            reserved_budget=original_nominal_risk*factor
            total_weights=1.
            if dca_enabled:
                weight=dca_size_multiplier
                for j in range(2,dca_levels+1):
                    total_weights+=weight
                    weight*=dca_size_multiplier
            if pyramid_enabled:
                weight=pyramid_size_multiplier
                for j in range(2,pyramid_levels+1):
                    total_weights+=weight
                    weight*=pyramid_size_multiplier
            total_qty=(reserved_budget/total_weights)/dist
            sum_entry_qty=px*total_qty
            dca_last=px
            pyramid_last=px
            dca_count=1
            pyramid_count=1
            trailing_started=False
            deals_today+=1
            if entry_mode!=0:
                # If this fill bar also spans the stop, assume adverse chronology.
                # Delaying that SL entirely would inflate pending-order backtests.
                pending_stop_hit=(lo[i]<=stop if side>0 else hi[i]>=stop)
                if not pending_stop_hit:
                    continue

        price=np.nan
        if pending_stop_hit:
            price=stop
        elif forced[i]:
            price=op[i]
        elif modeling==0:
            if side>0 and (op[i]<=stop or op[i]>=take):
                price=op[i]
            if side<0 and (op[i]>=stop or op[i]<=take):
                price=op[i]
        elif side>0:
            if op[i]<=stop:
                price=op[i]
            elif lo[i]<=stop:
                price=stop
            elif hi[i]>=take:
                price=take
        else:
            if op[i]>=stop:
                price=op[i]
            elif hi[i]>=stop:
                price=stop
            elif lo[i]<=take:
                price=take
        if not np.isfinite(price) and max_hold>0 and i-entry_bar+1>=max_hold:
            price=op[i] if modeling==0 else cl[i]
        if not np.isfinite(price) and i==end-1:
            price=op[i] if modeling==0 else cl[i]
        if np.isfinite(price):
            # All legs are charged for the full roundtrip at their entry price.
            result=side*(price*total_qty-sum_entry_qty)-sum_entry_qty*cost_bps/10000.
            r=result/max(original_nominal_risk,1e-15)
            outcome[count]=r
            exit_day[count]=days[i]
            count+=1
            if fixed_sizing:
                equity=max(0.,equity+result)
            else:
                equity=max(0.,equity+result)
            if r>0:
                wins+=1
                losses=0
                if risk_enabled:
                    if risk_mode==0:
                        risk_level=min(risk_max_levels-1,risk_level+1)
                    elif risk_reset_on_win:
                        risk_level=0
            elif r<0:
                losses+=1
                wins=0
                if risk_enabled:
                    if risk_mode==1:
                        risk_level=min(risk_max_levels-1,risk_level+1)
                    else:
                        risk_level=0
            if (max_wins>0 and wins>=max_wins) or (max_losses_streak>0 and losses>=max_losses_streak):
                frozen=True
            side=0
            last_exit=i
            continue

        if modeling!=0 and i>entry_bar:
            # Stop-first already evaluated. Ladder triggers after risk checks.
            a=atr[i-1]
            if np.isfinite(a) and a>0:
                scaled_dca=False
                if dca_enabled and dca_count<dca_levels:
                    spacing=_distance(dca_spacing_unit,dca_spacing,a,initial_dist,dca_last)
                    trigger=dca_last-side*spacing
                    hit=(lo[i]<=trigger if side>0 else hi[i]>=trigger)
                    if hit:
                        fill=(min(op[i],trigger) if side>0 else max(op[i],trigger))
                        if (fill-stop)*side>0:
                            weight=dca_size_multiplier**dca_count
                            added=(reserved_budget*weight/total_weights)/max(abs(fill-stop),1e-12)
                            total_qty+=added
                            sum_entry_qty+=added*fill
                            dca_last=fill
                            dca_count+=1
                            scaled_dca=True
                if pyramid_enabled and not scaled_dca and pyramid_count<pyramid_levels:
                    spacing=_distance(pyramid_spacing_unit,pyramid_spacing,a,initial_dist,pyramid_last)
                    trigger=pyramid_last+side*spacing
                    hit=(hi[i]>=trigger if side>0 else lo[i]<=trigger)
                    if hit:
                        fill=(max(op[i],trigger) if side>0 else min(op[i],trigger))
                        if (fill-stop)*side>0:
                            weight=pyramid_size_multiplier**pyramid_count
                            added=(reserved_budget*weight/total_weights)/max(abs(fill-stop),1e-12)
                            total_qty+=added
                            sum_entry_qty+=added*fill
                            pyramid_last=fill
                            pyramid_count+=1
                avg=sum_entry_qty/max(total_qty,1e-15)
                if tp_from_average and (dca_count>1 or pyramid_count>1):
                    take=avg+side*initial_take_dist

        # Complete bar values are only used to update stop for the NEXT bar.
        observed=op[i] if modeling==0 else cl[i]
        avatr=atr[i-1] if modeling==0 else atr[i]
        favorable=(observed-avg)*side
        if be_enabled:
            trigger=_distance(be_unit,be_trigger,avatr,initial_dist,avg)
            if favorable>=trigger:
                proposed=avg+side*be_offset
                if (proposed-stop)*side>0:
                    stop=proposed
        elif capital_be and favorable>=initial_dist*capital_be_r:
            if (avg-stop)*side>0:
                stop=avg
        if trail_enabled:
            activation=_distance(trail_activation_unit,trail_activation,avatr,initial_dist,avg)
            if favorable>=activation:
                trailing_started=True
            if trailing_started:
                distance=_distance(trail_distance_unit,trail_distance,avatr,initial_dist,avg)
                proposed=observed-side*distance
                if (proposed-stop)*side>0:
                    stop=proposed
        elif capital_trail and np.isfinite(avatr):
            proposed=observed-side*avatr*capital_trail_atr
            if (proposed-stop)*side>0:
                stop=proposed
    return outcome[:count],exit_day[:count]
