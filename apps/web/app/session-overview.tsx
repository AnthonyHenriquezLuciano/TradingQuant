"use client";

import { useEffect, useRef, useState } from "react";
import {
  ArrowRight, Check, ChevronRight, Clock3, Ellipsis, FileClock,
  FlaskConical, FolderPlus, Grid2X2, HelpCircle, Layers3, List,
  LoaderCircle, Play, Plus, Search, ShieldCheck, Sparkles, Trash2,
  TrendingUp, WandSparkles, X
} from "lucide-react";

export type AlgoSession<TConfig> = {
  id: string;
  name: string;
  symbol: string;
  createdAt: string;
  updatedAt: string;
  status: "draft" | "running" | "results";
  config: TConfig;
  runId?: string;
  found?: number;
};

type Props<TConfig> = {
  sessions: AlgoSession<TConfig>[];
  onCreate: (name: string) => void;
  onOpen: (sessionId: string) => void;
  onDelete: (sessionId: string) => void;
};

const format = (d: string) => {
  const dt = new Date(d);
  return Number.isNaN(dt.getTime())
    ? d
    : dt.toLocaleDateString("es-DO", {day:"2-digit",month:"short",year:"numeric"});
};

export function SessionOverview<TConfig>({sessions,onCreate,onOpen,onDelete}: Props<TConfig>) {
  const [layout,setLayout] = useState<"grid"|"list">("grid");
  const [search,setSearch] = useState("");
  const [menu,setMenu] = useState<string | null>(null);
  const [creating,setCreating] = useState(false);
  const [deleting,setDeleting] = useState<string | null>(null);
  const [help,setHelp] = useState(false);
  const [name,setName] = useState("");
  const [hydrated,setHydrated] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const nameRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem("tq_sessions_layout");
    if (stored === "grid" || stored === "list") setLayout(stored);
    setHydrated(true);
  }, []);
  useEffect(() => {if(hydrated) localStorage.setItem("tq_sessions_layout",layout)},[layout,hydrated]);
  useEffect(() => {
    const close = (e: PointerEvent) => {if(menuRef.current && !menuRef.current.contains(e.target as Node)) setMenu(null)};
    document.addEventListener("pointerdown",close);
    return () => document.removeEventListener("pointerdown",close);
  },[]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if(e.key === "Escape") {setMenu(null);setCreating(false);setDeleting(null)}
    };
    window.addEventListener("keydown",onKey);
    return () => window.removeEventListener("keydown",onKey);
  },[]);
  useEffect(() => {if(creating) nameRef.current?.focus()},[creating]);

  const withResults = sessions.filter(s => s.status === "results").length;
  const notStarted = sessions.filter(s => s.status === "draft").length;
  const working = sessions.filter(s => s.status === "running").length;
  const visible = sessions.filter(s => (s.name + " " + s.symbol).toLowerCase().includes(search.toLowerCase().trim()))
    .sort((a,b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
  const toDelete = sessions.find(s => s.id === deleting);
  const begin = () => {setName("");setMenu(null);setCreating(true)};
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    onCreate(name.trim());
    setCreating(false);
    setSearch("");
  };

  return <div className="sessions-page">
    <div className="sessions-head">
      <div className="sessions-title-group">
        <div className="eyebrow">LABORATORIO <span className="eyebrow-line"/> ESTRATEGY STUDIO</div>
        <div className="sessions-title-line"><h1>Creador de Algoritmos</h1><button className="sessions-help-link" onClick={()=>setHelp(v=>!v)} aria-expanded={help}><HelpCircle size={15}/> ¿Cómo usar esta sección?</button></div>
        <p>Genera, explora y evoluciona algoritmos de trading desde un solo espacio de trabajo.</p>
      </div>
      <button className="btn sessions-create-button" onClick={begin}><Plus size={17}/> Nueva Sesión</button>
    </div>

    {help&&<section className="sessions-guide" aria-label="Cómo utilizar las sesiones">
      <div className="sessions-guide-icon"><Sparkles size={18}/></div>
      <div><strong>Del concepto al experimento.</strong><p>Crea una sesión con su nombre y mercado. Después ábrela para configurar datos históricos, señales, riesgo y validación. Los resultados se consultan desde «Exploraciones»; el acceso directo desde las tarjetas llegará próximamente.</p></div>
      <button onClick={()=>setHelp(false)} aria-label="Cerrar ayuda"><X size={17}/></button>
    </section>}

    <div className="sessions-stats" aria-label="Resumen de sesiones">
      <div className="sessions-stat"><span className="sessions-stat-icon"><WandSparkles size={20}/></span><div><span className="sessions-stat-label">Sesiones</span><strong>{sessions.length}</strong><span className="sessions-stat-sub">Espacios de investigación creados</span></div><span className="sessions-stat-number">01</span></div>
      <div className="sessions-stat"><span className="sessions-stat-icon"><ShieldCheck size={20}/></span><div><span className="sessions-stat-label">Con Resultados</span><strong>{withResults}</strong><span className="sessions-stat-sub">Exploraciones completadas</span></div><span className="sessions-stat-number">02</span></div>
      <div className="sessions-stat"><span className="sessions-stat-icon"><FileClock size={20}/></span><div><span className="sessions-stat-label">Sin Iniciar</span><strong>{notStarted}</strong><span className="sessions-stat-sub">Pendientes de ejecución{working>0?" · "+working+" en curso":""}</span></div><span className="sessions-stat-number">03</span></div>
    </div>

    <div className="sessions-workspace-head">
      <div className="sessions-collection-heading"><span className="sessions-collection-rule"/><span>ESPACIOS DE TRABAJO</span><h2>Mis sesiones <span>{sessions.length}</span></h2></div>
      <div className="sessions-toolbar">
        {sessions.length>0&&<label className="sessions-search"><Search size={15}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Buscar sesión..." aria-label="Buscar sesiones"/></label>}
        <div className="sessions-view-switch" role="group" aria-label="Visualización">
          <button title="Vista compacta" aria-label="Vista compacta" aria-pressed={layout==="grid"} className={layout==="grid"?"is-active":""} onClick={()=>setLayout("grid")}><Grid2X2 size={17}/></button>
          <button title="Vista de lista" aria-label="Vista de lista" aria-pressed={layout==="list"} className={layout==="list"?"is-active":""} onClick={()=>setLayout("list")}><List size={18}/></button>
        </div>
      </div>
    </div>

    {sessions.length === 0
      ? <div className="sessions-empty">
        <div className="sessions-empty-art"><Layers3 size={28}/><span/></div>
        <h3>Todo empieza con una sesión.</h3>
        <p>Crea tu primer espacio para organizar hipótesis, configurar algoritmos y documentar cada búsqueda.</p>
        <button className="btn sessions-create-button" onClick={begin}><Plus size={16}/> Crear mi primera sesión</button>
        <small>Las sesiones se guardan por ahora en este navegador.</small>
      </div>
      : visible.length === 0
      ? <div className="sessions-empty sessions-search-empty"><Search size={24}/><h3>No encontramos sesiones</h3><p>Prueba otro nombre o símbolo.</p><button onClick={()=>setSearch("")}>Limpiar búsqueda <ArrowRight size={15}/></button></div>
      : <div className={layout==="grid"?"sessions-tiles":"sessions-tiles sessions-tiles-list"}>
        {visible.map(session => {
          const hasResults = session.status === "results";
          const isRunning = session.status === "running";
          return <article className="session-tile" key={session.id}>
            <div className="session-tile-top">
              <div className="session-market"><span className={"session-market-dot "+(hasResults?"is-ready":isRunning?"is-busy":"")}/><div><strong>{session.name}</strong><span>{session.symbol} <span className="session-divider-dot">·</span> Estrategia cuantitativa</span></div></div>
              <div ref={menu===session.id?menuRef:undefined} className="session-menu-wrap">
                <button className="session-more" title="Acciones de la sesión" aria-label={"Opciones de "+session.name} aria-haspopup="menu" aria-expanded={menu===session.id} onClick={()=>setMenu(v=>v===session.id?null:session.id)}><Ellipsis size={20}/></button>
                {menu===session.id&&<div className="session-dropdown" role="menu">
                  <button role="menuitem" disabled aria-disabled="true" title="Próximamente"><TrendingUp size={16}/><span>Ver resultados<small>Próximamente</small></span></button>
                  <div className="session-menu-separator"/>
                  <button role="menuitem" className="session-delete-option" onClick={()=>{setDeleting(session.id);setMenu(null)}}><Trash2 size={16}/> Eliminar sesión</button>
                </div>}
              </div>
            </div>
            <div className="session-tile-middle">
              <span className={"session-status "+(hasResults?"status-results":isRunning?"status-running":"status-draft")}>{hasResults?<ShieldCheck size={12}/>:isRunning?<LoaderCircle className="spin" size={12}/>:<Clock3 size={12}/>} {hasResults?"Con resultados":isRunning?"En ejecución":"Sin iniciar"}</span>
              {hasResults&&<span className="session-result-count">{session.found??0} estrategias evaluadas</span>}
              {!hasResults&&<span className="session-draft-description">Lista para configurar y explorar estrategias.</span>}
            </div>
            <div className="session-tile-footer">
              <span><Clock3 size={13}/> Creada el {format(session.createdAt)}</span>
              <button onClick={()=>onOpen(session.id)}>{isRunning?"Revisar configuración":hasResults?"Abrir sesión":"Configurar sesión"} <ChevronRight size={17}/></button>
            </div>
          </article>;
        })}
      </div>
    }
    <div className="sessions-bottom-note"><span className="sessions-note-dot"/> WORKSPACE PERSONAL <span>·</span> Investigación en fase beta <span>·</span> Guardado local del navegador</div>

    {creating&&<div className="session-modal-overlay" onMouseDown={e=>{if(e.target===e.currentTarget)setCreating(false)}}>
      <div className="session-modal" role="dialog" aria-modal="true" aria-labelledby="new-session-title">
        <div className="session-modal-header"><div className="session-modal-symbol"><FolderPlus size={21}/></div><button onClick={()=>setCreating(false)} aria-label="Cerrar"><X size={19}/></button></div>
        <div className="eyebrow">NUEVA INVESTIGACIÓN / 01</div>
        <h2 id="new-session-title">Crear nueva sesión</h2>
        <p>Organiza una hipótesis de trading bajo su propio espacio de trabajo.</p>
        <form onSubmit={submit}>
          <label>Nombre de la sesión<input ref={nameRef} maxLength={80} required value={name} onChange={e=>setName(e.target.value)} placeholder="Ej. Nasdaq100 · Rupturas de Londres"/></label>
          <div className="session-modal-actions"><button type="button" className="btn session-cancel" onClick={()=>setCreating(false)}>Cancelar</button><button type="submit" className="btn sessions-create-button" disabled={!name.trim()}><Plus size={17}/> Crear sesión</button></div>
        </form>
      </div>
    </div>}
    {toDelete&&<div className="session-modal-overlay" onMouseDown={e=>{if(e.target===e.currentTarget)setDeleting(null)}}>
      <div className="session-modal session-delete-modal" role="alertdialog" aria-modal="true" aria-labelledby="delete-session-title">
        <div className="session-modal-header"><div className="session-modal-symbol destructive"><Trash2 size={20}/></div><button onClick={()=>setDeleting(null)} aria-label="Cerrar"><X size={19}/></button></div>
        <h2 id="delete-session-title">¿Eliminar esta sesión?</h2>
        <p>Se eliminará «{toDelete.name}» y su resultado asociado de este navegador. Esta acción no se puede deshacer.</p>
        <div className="session-modal-actions"><button className="btn session-cancel" onClick={()=>setDeleting(null)}>Cancelar</button><button className="btn session-confirm-delete" onClick={()=>{onDelete(toDelete.id);setDeleting(null)}}><Trash2 size={16}/> Eliminar sesión</button></div>
      </div>
    </div>}
  </div>;
}
