import * as apiClient from "./api/client.js";
import * as apiClient from "./api/client.js";
import { useState, useEffect, useRef } from "react";
import { AreaChart, Area, BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell, RadialBarChart, RadialBar } from "recharts";
import { GeoMap, JetTracker, FootTraffic, Satellite, PermitRadar } from "./pages/GeoPages.jsx";
import { LiveTriggers, BDCoaching, GhostStudio } from "./pages/NewModules.jsx";

/* ─── Google Fonts ─────────────────────────────────────────────────────────── */
const FontLoader = () => (
  <style>{`
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;0,700;0,900;1,400;1,700&family=DM+Mono:ital,wght@0,300;0,400;0,500;1,300&family=Lato:ital,wght@0,300;0,400;0,700;1,400&display=swap');

    *, *::before, *::after { margin:0; padding:0; box-sizing:border-box; }

    :root {
      --bg:       #06080e;
      --panel:    #0a0e18;
      --card:     #0e1420;
      --elevated: #121826;
      --border:   rgba(255,255,255,0.055);
      --border2:  rgba(255,255,255,0.09);
      --border3:  rgba(255,255,255,0.14);

      --gold:     #c49a3a;
      --gold2:    #e0b558;
      --golddim:  rgba(196,154,58,0.12);
      --goldglow: rgba(196,154,58,0.20);
      --red:      #c74040;
      --reddim:   rgba(199,64,64,0.10);
      --redglow:  rgba(199,64,64,0.22);
      --green:    #2a9e62;
      --greendim: rgba(42,158,98,0.10);
      --blue:     #4282e8;
      --bluedim:  rgba(66,130,232,0.10);
      --cyan:     #1cbcc7;
      --purple:   #8a5ef0;

      --t1:#e6e0d6;
      --t2:#7a8a9e;
      --t3:#364454;
      --t4:#1a2535;

      --serif:  'Playfair Display', Georgia, serif;
      --mono:   'DM Mono', monospace;
      --sans:   'Lato', system-ui, sans-serif;
      --sidebar-w: 232px;
    }

    html, body, #root { height:100%; background:var(--bg); overflow:hidden; }
    body { font-family:var(--sans); font-size:13px; color:var(--t1); -webkit-font-smoothing:antialiased; }
    ::-webkit-scrollbar { width:3px; height:3px; }
    ::-webkit-scrollbar-track { background:transparent; }
    ::-webkit-scrollbar-thumb { background:var(--border2); border-radius:2px; }
    button { cursor:pointer; font-family:var(--sans); }
    input, textarea { font-family:var(--sans); }

    @keyframes fadeUp  { from{opacity:0;transform:translateY(6px)} to{opacity:1;transform:translateY(0)} }
    @keyframes pulse   { 0%,100%{opacity:1} 50%{opacity:0.3} }
    @keyframes spin    { to{transform:rotate(360deg)} }
    @keyframes ticker  { 0%{transform:translateX(0)} 100%{transform:translateX(-50%)} }
    @keyframes glow    { 0%,100%{box-shadow:0 0 0 transparent} 50%{box-shadow:0 0 18px var(--goldglow)} }

    .fadeup{animation:fadeUp .28s ease both}
    .s1{animation-delay:.04s}.s2{animation-delay:.08s}.s3{animation-delay:.12s}
    .s4{animation-delay:.16s}.s5{animation-delay:.20s}.s6{animation-delay:.24s}
    .pulse{animation:pulse 2.4s ease-in-out infinite}
    .spin{animation:spin .7s linear infinite}
  `}</style>
);

/* ─── Data ──────────────────────────────────────────────────────────────────── */
const D = {
  firm: "Blackstone Meridian LLP",
  clients: [
    { id:1,name:"Aurelia Capital Group",industry:"Asset Mgmt",churn:78,wallet:12,spend:8400000,rev:1020000,risk:"critical",partner:"S. Chen",contact:3,matter:"M&A Advisory",pgs:["M&A","Securities"],region:"Toronto" },
    { id:2,name:"Vantage Rail Corp",industry:"Infrastructure",churn:61,wallet:23,spend:3100000,rev:712000,risk:"high",partner:"M. Webb",contact:8,matter:"Regulatory Defense",pgs:["Regulatory","Employment"],region:"Calgary" },
    { id:3,name:"Centurion Pharma",industry:"Life Sciences",churn:44,wallet:31,spend:2200000,rev:680000,risk:"medium",partner:"D. Park",contact:12,matter:"IP Litigation",pgs:["IP","Litigation"],region:"Mississauga" },
    { id:4,name:"Northfield Energy",industry:"Oil & Gas",churn:18,wallet:41,spend:9100000,rev:3731000,risk:"low",partner:"J. Okafor",contact:2,matter:"JV Structuring",pgs:["M&A","Finance","Environmental"],region:"Calgary" },
    { id:5,name:"Ember Financial",industry:"Banking",churn:22,wallet:8,spend:18200000,rev:1456000,risk:"low",partner:"S. Chen",contact:1,matter:"OSFI Compliance",pgs:["Banking","Securities"],region:"Toronto" },
    { id:6,name:"Solaris Construction",industry:"Real Estate",churn:87,wallet:17,spend:890000,rev:151300,risk:"critical",partner:"P. Rodrigues",contact:41,matter:"Construction Dispute",pgs:["Litigation","Real Estate"],region:"Vancouver" },
    { id:7,name:"Meridian Logistics",industry:"Transportation",churn:53,wallet:19,spend:2700000,rev:513000,risk:"medium",partner:"M. Webb",contact:15,matter:"Customs Dispute",pgs:["Trade","Litigation"],region:"Montreal" },
    { id:8,name:"ClearPath Technologies",industry:"Technology",churn:29,wallet:45,spend:620000,rev:279000,risk:"low",partner:"D. Park",contact:5,matter:"Series C Financing",pgs:["Finance","IP"],region:"Waterloo" },
  ],
  churnSignals: {
    1:["Billing frequency dropped 38%","GC replaced 6 weeks ago","2 invoices disputed in 90 days","New associate assigned mid-matter","Reply latency increased 4.2×"],
    6:["No contact in 41 days","Project update request — ignored","LinkedIn: GC visiting competitor offices","Matter stalled at client's instruction","Lead partner leaving firm"],
    2:["Budget dispute unresolved","CFO: 'reducing outside counsel spend'","3 junior billing write-offs in Q3","Partner response time increased"],
    7:["Associate changed twice on one matter","Billing rhythm slowed monthly→quarterly"],
  },
  prospects: [
    { name:"Arctis Mining Corp",score:94,need:"M&A Advisory",warmth:"warm",value:"$680K",window:"2–4 wks",signals:["SEDAR: 3 confidentiality agreements filed","CFO departure announced","M&A banker LinkedIn spike","Competitor acquisition same week"] },
    { name:"Pinnacle Health Systems",score:88,need:"Regulatory Defense",warmth:"warm",value:"$420K",window:"1–3 wks",signals:["Health Canada inspection notice","CIO resigned","Glassdoor compliance keywords +340%","GC LinkedIn activity ×5"] },
    { name:"Westbrook Digital Corp",score:81,need:"Privacy / Data Breach",warmth:"cold",value:"$290K",window:"48 hrs",signals:["Credentials on BreachForums 03:14 AM","IT hiring +200% past 60 days","Privacy policy page deleted","CISO role posted"] },
    { name:"Stellex Infrastructure Fund",score:76,need:"Fund Restructuring",warmth:"lukewarm",value:"$1.1M",window:"4–8 wks",signals:["Investor redemption notice filed","LP concentration risk in 40-F","3 LP board seats changed"] },
    { name:"Borealis Genomics Inc.",score:69,need:"IP Licensing + Series C",warmth:"warm",value:"$380K",window:"6–10 wks",signals:["17 new PCT patent filings Q3","Trademark filings in 7 jurisdictions","VP BD hired from Moderna"] },
    { name:"Caldwell Steel Works",score:63,need:"Employment / WSIB",warmth:"cold",value:"$220K",window:"2–4 wks",signals:["3 WSIB inspection orders in 90 days","Mass layoff notice filed","HR Director + VP Operations departed"] },
  ],
  regAlerts: [
    { id:"REG-001",src:"OSFI",title:"Guideline B-20 Amendment — Mortgage Stress Testing",date:"Nov 12",sev:"high",affected:[5],pa:"Banking & Finance",ready:true },
    { id:"REG-002",src:"OSC",title:"NI 45-106 Offering Memorandum Regime Update",date:"Nov 08",sev:"medium",affected:[1,5],pa:"Securities",ready:true },
    { id:"REG-003",src:"CSA",title:"Staff Notice 51-363: Cannabis Sector Issuers",date:"Nov 05",sev:"low",affected:[3],pa:"Regulatory",ready:false },
    { id:"REG-004",src:"ECCC",title:"Clean Electricity Regulations — Final Rule",date:"Oct 29",sev:"high",affected:[4,2],pa:"Environmental",ready:false },
    { id:"REG-005",src:"FINTRAC",title:"AML Beneficial Ownership Threshold Changes",date:"Oct 20",sev:"high",affected:[1,5,8],pa:"Banking & Finance",ready:true },
  ],
  competitors: [
    { firm:"Davies Ward Phillips",signal:"Partner J. Holbrook (ex-Blackstone Meridian) now advising Aurelia Capital",level:"critical",clients:["Aurelia Capital Group"],cat:"Alumni Threat",date:"Oct 15" },
    { firm:"Osler Hoskin",signal:"Hired 4 M&A laterals with fintech background — targeting your clients",level:"high",clients:["Aurelia Capital","Ember Financial"],cat:"Lateral Hire",date:"Oct 28" },
    { firm:"Stikeman Elliott",signal:"New Energy Transition practice group announced",level:"medium",clients:["Northfield Energy"],cat:"Practice Expansion",date:"Nov 01" },
    { firm:"Blake Cassels",signal:"Sponsoring CLEs attended by Meridian Logistics GC",level:"medium",clients:["Meridian Logistics"],cat:"Event Presence",date:"Nov 10" },
  ],
  alumni: [
    { name:"Tom Hartley",role:"Deputy GC",company:"Westbrook Digital Corp",left:2019,mentor:"D. Park",warmth:92,trigger:"Data breach signal — call within 48 hrs",active:true },
    { name:"Sarah Yuen",role:"General Counsel",company:"Pinnacle Health Systems",left:2021,mentor:"D. Park",warmth:88,trigger:"Health Canada inspection — regulatory mandate",active:true },
    { name:"Derek Ma",role:"VP Legal & Compliance",company:"Stellex Infrastructure Fund",left:2020,mentor:"J. Okafor",warmth:74,trigger:"Fund restructuring signal detected",active:true },
    { name:"Monica Baptiste",role:"Senior Counsel",company:"Borealis Genomics",left:2018,mentor:"D. Park",warmth:61,trigger:null,active:false },
    { name:"Hassan Khalil",role:"Legal Counsel",company:"Arcadia Power Ltd.",left:2022,mentor:"M. Webb",warmth:45,trigger:null,active:false },
  ],
  maDark: [
    { company:"Arctis Mining Corp",confidence:91,type:"Sale Process (Sell-Side)",value:"$2.1B–$2.8B",days:"14–28",warmth:18,signals:["Options volume 340% above 90-day avg","CEO jet: Bay Street 3× in 10 days","Lazard banker LinkedIn spike","Confidential treatment request on SEDAR"] },
    { company:"Stellex Infrastructure Fund",confidence:74,type:"Portfolio Restructuring / Recap",value:"$800M–$1.4B",days:"30–60",warmth:44,signals:["LP redemption pressure","External restructuring advisor retained","Audit committee director resigned"] },
    { company:"Vesta Retail REIT",confidence:68,type:"REIT Privatization",value:"$600M–$900M",days:"45–90",warmth:5,signals:["CRE broker clusters near HQ","CEO attending CBRE PE summit","3 subsidiary name changes in 60 days"] },
  ],
  pipeline:[
    {m:"Jun",pipe:4.2,closed:1.8,acts:42},{m:"Jul",pipe:4.8,closed:2.1,acts:38},
    {m:"Aug",pipe:3.9,closed:1.4,acts:31},{m:"Sep",pipe:5.2,closed:2.6,acts:51},
    {m:"Oct",pipe:6.1,closed:2.9,acts:48},{m:"Nov",pipe:7.4,closed:3.1,acts:55},
  ],
  pitches:[
    {q:"Q1 '25",won:8,lost:3,rate:72.7},{q:"Q2 '25",won:5,lost:6,rate:45.5},
    {q:"Q3 '25",won:7,lost:4,rate:63.6},
  ],
};

const fmt = n => n>=1e6?`$${(n/1e6).toFixed(1)}M`:n>=1e3?`$${(n/1e3).toFixed(0)}K`:`$${n}`;
const riskColor = r => ({critical:"#e05252",high:"#e07c30",medium:"#d4a843",low:"#3dba7a"}[r]||"#6a89b4");
const scoreColor = s => s>=75?"#e05252":s>=50?"#e07c30":s>=30?"#d4a843":"#3dba7a";
const warmthColor = w => w>=80?"#3dba7a":w>=60?"#d4a843":w>=40?"#4a8fff":"#6a89b4";

/* ─── Shared UI ─────────────────────────────────────────────────────────────── */
const T = ({ch,color="dim",style={}})=>{
  const m={
    dim:  {bg:"rgba(255,255,255,0.04)",br:"var(--border2)",tx:"var(--t2)"},
    gold: {bg:"var(--golddim)",        br:"rgba(196,154,58,.28)",tx:"var(--gold2)"},
    red:  {bg:"var(--reddim)",         br:"rgba(199,64,64,.28)", tx:"#e05555"},
    green:{bg:"var(--greendim)",       br:"rgba(42,158,98,.28)", tx:"#34bb76"},
    blue: {bg:"var(--bluedim)",        br:"rgba(66,130,232,.28)",tx:"#6aaeff"},
    purple:{bg:"rgba(138,94,240,.10)", br:"rgba(138,94,240,.28)",tx:"#a87fff"},
  };
  const s=m[color]||m.dim;
  return(
    <span style={{background:s.bg,border:`1px solid ${s.br}`,color:s.tx,
      fontSize:9,fontFamily:"var(--mono)",letterSpacing:".07em",
      padding:"2px 7px",borderRadius:2,whiteSpace:"nowrap",fontWeight:500,...style}}>{ch}</span>
  );
};
const Dot = ({c,pulse})=><span style={{width:6,height:6,borderRadius:"50%",background:c,display:"inline-block",flexShrink:0,animation:pulse?"pulse 2s ease-in-out infinite":""}}/>
const Spinner = ()=>(
  <div style={{display:"flex",alignItems:"center",gap:8,color:"var(--t3)",fontSize:11,fontFamily:"var(--mono)"}}>
    <div className="spin" style={{width:13,height:13,border:"2px solid var(--border2)",borderTopColor:"var(--gold)",borderRadius:"50%"}}/>
    Generating intelligence…
  </div>
);
const SBar = ({s,color,noNum})=>{
  const c=color||(s>=75?"#e05252":s>=50?"#e07c30":s>=30?"#d4a843":"#3dba7a");
  return(
    <div style={{display:"flex",alignItems:"center",gap:8}}>
      <div style={{flex:1,height:3,background:"var(--border)",borderRadius:2,overflow:"hidden"}}>
        <div style={{width:`${s}%`,height:"100%",background:c,borderRadius:2,transition:"width .8s ease"}}/>
      </div>
      <span style={{fontFamily:"var(--mono)",fontSize:11,color:c,width:24,textAlign:"right"}}>{s}</span>
    </div>
  );
};
const Metric = ({label,val,change,dir,sub,accent="gold"})=>{
  // upgraded
  const cols={gold:"var(--gold)",red:"var(--red)",green:"var(--green)",blue:"var(--blue)",purple:"var(--purple)",default:"var(--t1)"};
  return(
    <div style={{background:"var(--card)",border:"1px solid var(--border)",borderRadius:3,padding:"14px 16px",position:"relative",overflow:"hidden"}}>
      <div style={{fontSize:9,fontFamily:"var(--mono)",color:"var(--t3)",letterSpacing:".12em",textTransform:"uppercase",marginBottom:10}}>{label}</div>
      <div style={{fontFamily:"var(--mono)",fontSize:26,fontWeight:500,color:cols[accent]||cols.default,lineHeight:1}}>{val}</div>
      {(change||sub)&&<div style={{marginTop:7,fontSize:10,display:"flex",gap:6,alignItems:"center"}}>
        {change&&<span style={{color:dir==="up"?"var(--green)":dir==="dn"?"var(--red)":"var(--t3)"}}>{dir==="up"?"↑":dir==="dn"?"↓":"→"} {Math.abs(change)}%</span>}
        {sub&&<span style={{color:"var(--t3)",fontFamily:"var(--mono)"}}>{sub}</span>}
      </div>}
      <div style={{position:"absolute",bottom:0,left:0,right:0,height:1,background:cols[accent]||cols.default,opacity:0.4}}/>
    </div>
  );
};
const Panel = ({title,children,actions,style={}})=>(
  <div style={{background:"var(--card)",border:"1px solid var(--border)",borderRadius:3,...style}}>
    {title&&<div style={{padding:"11px 16px",borderBottom:"1px solid var(--border)",display:"flex",justifyContent:"space-between",alignItems:"center"}}>
      <span style={{fontFamily:"var(--mono)",fontSize:9,color:"var(--t2)",letterSpacing:".10em",textTransform:"uppercase",fontWeight:500}}>{title}</span>
      {actions}
    </div>}
    {children}
  </div>
);
const AiBadge = ()=><T ch="◈ AI" color="gold"/>;
const PageHeader = ({tag,title,sub})=>(
  <div style={{marginBottom:22,paddingBottom:18,borderBottom:"1px solid var(--border)"}}>
    {tag&&<div style={{fontFamily:"var(--mono)",fontSize:9,color:"var(--gold)",letterSpacing:".16em",marginBottom:8,textTransform:"uppercase"}}>{tag}</div>}
    <h1 style={{fontFamily:"var(--serif)",fontWeight:700,fontSize:24,fontStyle:"italic",letterSpacing:"-.01em",marginBottom:5,color:"var(--t1)",lineHeight:1.1}}>{title}</h1>
    {sub&&<p style={{color:"var(--t2)",fontSize:12,lineHeight:1.65,maxWidth:640}}>{sub}</p>}
  </div>
);
const CTip = ({active,payload,label})=>{
  if(!active||!payload?.length)return null;
  return<div style={{background:"var(--elevated)",border:"1px solid var(--border2)",padding:"8px 12px",borderRadius:3,fontSize:11}}>
    <div style={{color:"var(--t3)",fontFamily:"var(--mono)",marginBottom:4}}>{label}</div>
    {payload.map(p=><div key={p.name} style={{color:p.color||p.stroke,fontFamily:"var(--mono)"}}>{p.name}: {typeof p.value==="number"&&p.value<200?p.value>10?p.value.toFixed(1):p.value:fmt(p.value*1000000||p.value)}</div>)}
  </div>;
};
const OBtn = ({children,onClick,disabled,secondary,small})=>(
  <button onClick={onClick} disabled={disabled} style={{
    padding:small?"5px 12px":"7px 16px",borderRadius:2,
    fontFamily:"var(--mono)",fontSize:10,fontWeight:500,letterSpacing:".07em",textTransform:"uppercase",
    border:secondary?"1px solid var(--border2)":"none",
    background:secondary?"transparent":disabled?"var(--golddim)":"var(--gold)",
    color:secondary?"var(--t2)":disabled?"rgba(196,154,58,.4)":"#06080e",
    cursor:disabled?"not-allowed":"pointer",transition:"all .15s",opacity:disabled?.55:1,
  }}>{children}</button>
);

/* ─── NAV ────────────────────────────────────────────────────────────────────── */
const NAV = [
  {group:"INTELLIGENCE",items:[
    {id:"cmd",icon:"◈",label:"Command Center"},
    {id:"churn",icon:"⚠",label:"Churn Predictor"},
    {id:"reg",icon:"⚡",label:"Regulatory Ripple"},
    {id:"heat",icon:"◫",label:"Relationship Map"},
    {id:"triggers",icon:"↯",label:"Live Triggers"},
  ]},
  {group:"GEOSPATIAL",items:[
    {id:"geomap",icon:"⊙",label:"Mandate Heat Map"},
    {id:"jets",icon:"✈",label:"Jet Tracker"},
    {id:"foot",icon:"◉",label:"Foot Traffic Intel"},
    {id:"sat",icon:"◎",label:"Satellite Signals"},
    {id:"permits",icon:"⊞",label:"Permit Radar"},
  ]},
  {group:"ACQUISITION",items:[
    {id:"precrime",icon:"◉",label:"Pre-Crime Engine"},
    {id:"mandates",icon:"↯",label:"Mandate Formation"},
    {id:"ma",icon:"◎",label:"M&A Dark Signals"},
  ]},
  {group:"INTEL OPS",items:[
    {id:"comp",icon:"⊗",label:"Competitor Radar"},
    {id:"wallet",icon:"◑",label:"Wallet Share"},
    {id:"alumni",icon:"◇",label:"Alumni Activator"},
    {id:"gc",icon:"◈",label:"GC Profiler"},
  ]},
  {group:"DEVELOPMENT",items:[
    {id:"assoc",icon:"△",label:"Associate Accelerator"},
    {id:"pitch",icon:"⊕",label:"Pitch Autopsy"},
    {id:"coaching",icon:"◑",label:"BD Coaching"},
    {id:"ghost",icon:"◈",label:"Ghost Studio"},
  ]},
];

const Sidebar = ({active,set})=>(
  <div style={{width:210,minWidth:210,background:"var(--panel)",borderRight:"1px solid var(--border)",display:"flex",flexDirection:"column",overflow:"hidden"}}>
    {/* Logo */}
    <div style={{padding:"18px 14px 14px",borderBottom:"1px solid var(--border)"}}>
      <div style={{display:"flex",alignItems:"center",gap:10,marginBottom:8}}>
        <div style={{width:30,height:30,background:"var(--gold)",borderRadius:3,display:"flex",alignItems:"center",justifyContent:"center",fontFamily:"var(--serif)",fontWeight:800,fontSize:15,color:"var(--ink)",flexShrink:0,animation:"glow 3s ease-in-out infinite"}}>O</div>
        <div>
          <div style={{fontFamily:"var(--serif)",fontWeight:800,fontSize:17,letterSpacing:"-.01em",color:"var(--t1)"}}>ORACLE</div>
          <div style={{fontSize:8,color:"var(--t3)",letterSpacing:".12em",fontFamily:"var(--mono)",marginTop:1}}>INTELLIGENCE OS</div>
        </div>
      </div>
      <div style={{fontSize:9,color:"var(--t3)",background:"var(--elevated)",borderRadius:2,padding:"4px 8px",fontFamily:"var(--mono)",letterSpacing:".02em"}}>{D.firm}</div>
    </div>
    {/* Nav */}
    <div style={{flex:1,padding:"10px 8px",overflowY:"auto",display:"flex",flexDirection:"column",gap:2}}>
      {NAV.map(s=>(
        <div key={s.group} style={{marginBottom:6}}>
          <div style={{fontSize:8,fontFamily:"var(--mono)",color:"var(--t4)",letterSpacing:".14em",padding:"6px 8px 3px"}}>{s.group}</div>
          {s.items.map(item=>(
            <button key={item.id} onClick={()=>set(item.id)} style={{width:"100%",display:"flex",alignItems:"center",gap:9,padding:"7px 10px",borderRadius:3,border:`1px solid ${active===item.id?"rgba(212,168,67,.25)":"transparent"}`,background:active===item.id?"rgba(212,168,67,.07)":"transparent",color:active===item.id?"var(--gold)":"var(--t2)",fontSize:12,fontWeight:500,textAlign:"left",transition:"all .1s",letterSpacing:".01em"}}>
              <span style={{fontSize:12,width:14,textAlign:"center",flexShrink:0}}>{item.icon}</span>
              {item.label}
            </button>
          ))}
        </div>
      ))}
    </div>
    {/* Status */}
    <div style={{padding:"10px 14px",borderTop:"1px solid var(--border)",fontSize:9,color:"var(--t3)",fontFamily:"var(--mono)"}}>
      <div style={{display:"flex",alignItems:"center",gap:6,marginBottom:3}}>
        <Dot c="#3dba7a" pulse/> All signal feeds active
      </div>
      <div>v2.4.1 · Nov 2025</div>
    </div>
  </div>
);

/* ─── COMMAND CENTER ─────────────────────────────────────────────────────────── */
const CommandCenter = ({setPage})=>{
  const [tick,setTick]=useState(new Date());
  useEffect(()=>{const t=setInterval(()=>setTick(new Date()),1000);return()=>clearInterval(t)},[]);
  const atRisk=D.clients.filter(c=>c.churn>=60);
  return(
    <div style={{height:"100%",overflowY:"auto",padding:"20px 24px"}}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:20}}>
        <div>
          <div style={{fontFamily:"var(--mono)",fontSize:9,color:"var(--gold)",letterSpacing:".14em",marginBottom:5}}>◈ ORACLE INTELLIGENCE OS · COMMAND CENTER</div>
          <h1 style={{fontFamily:"var(--serif)",fontWeight:800,fontSize:24,letterSpacing:"-.03em",color:"var(--t1)"}}>{D.firm}</h1>
        </div>
        <div style={{textAlign:"right"}}>
          <div style={{fontFamily:"var(--mono)",fontSize:20,color:"var(--gold)",letterSpacing:".04em"}}>{tick.toLocaleTimeString("en-CA",{hour12:false})}</div>
          <div style={{fontSize:9,color:"var(--t3)",fontFamily:"var(--mono)",marginTop:2}}>{tick.toLocaleDateString("en-CA",{weekday:"short",year:"numeric",month:"short",day:"numeric"})}</div>
        </div>
      </div>
      {/* KPIs */}
      <div className="fadeup" style={{display:"grid",gridTemplateColumns:"repeat(5,1fr)",gap:10,marginBottom:16}}>
        <Metric label="Active Pipeline" val="$7.4M" change={21} dir="up" sub="vs last month" accent="gold"/>
        <Metric label="Clients at Risk" val={atRisk.length} sub="flight-risk signals" accent="red"/>
        <Metric label="Top Prospects" val={D.prospects.length} sub="pre-crime signals" accent="blue"/>
        <Metric label="Pitch Win Rate" val="63.6%" change={18} dir="up" sub="vs prior quarter" accent="green"/>
        <Metric label="Avg Wallet Share" val="24.5%" change={3} dir="up" sub="of client spend" accent="purple"/>
      </div>
      {/* Main grid */}
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12,marginBottom:12}}>
        {/* Pipeline chart */}
        <Panel title="BD Pipeline — 6 Months">
          <div style={{padding:"14px 16px"}}>
            <ResponsiveContainer width="100%" height={150}>
              <AreaChart data={D.pipeline}>
                <defs>
                  <linearGradient id="pg" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#d4a843" stopOpacity={.2}/><stop offset="95%" stopColor="#d4a843" stopOpacity={0}/></linearGradient>
                  <linearGradient id="cg" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#4a8fff" stopOpacity={.2}/><stop offset="95%" stopColor="#4a8fff" stopOpacity={0}/></linearGradient>
                </defs>
                <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false}/>
                <XAxis dataKey="m" tick={{fill:"var(--t3)",fontSize:9,fontFamily:"'DM Mono'"}} axisLine={false} tickLine={false}/>
                <YAxis tick={{fill:"var(--t3)",fontSize:9,fontFamily:"'DM Mono'"}} axisLine={false} tickLine={false} tickFormatter={v=>`$${v}M`}/>
                <Tooltip content={<CTip/>}/>
                <Area type="monotone" dataKey="pipe" name="Pipeline($M)" stroke="#d4a843" fill="url(#pg)" strokeWidth={1.5} dot={false}/>
                <Area type="monotone" dataKey="closed" name="Closed($M)" stroke="#4a8fff" fill="url(#cg)" strokeWidth={1.5} dot={false}/>
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Panel>
        {/* At risk */}
        <Panel title="Clients at Flight Risk" actions={<button onClick={()=>setPage("churn")} style={{fontSize:9,color:"var(--gold)",background:"none",border:"none",fontFamily:"var(--mono)",letterSpacing:".06em",cursor:"pointer"}}>VIEW ALL →</button>}>
          <div style={{padding:"12px 14px",display:"flex",flexDirection:"column",gap:10}}>
            {atRisk.map(c=>(
              <div key={c.id}>
                <div style={{display:"flex",justifyContent:"space-between",marginBottom:4}}>
                  <div><div style={{fontSize:12,fontWeight:500,color:"var(--t1)"}}>{c.name}</div><div style={{fontSize:10,color:"var(--t3)"}}>{c.partner} · {c.industry}</div></div>
                  <span style={{fontSize:8,fontFamily:"var(--mono)",background:`${riskColor(c.risk)}18`,border:`1px solid ${riskColor(c.risk)}40`,color:riskColor(c.risk),padding:"2px 6px",borderRadius:2,height:"fit-content"}}>{c.risk.toUpperCase()}</span>
                </div>
                <SBar s={c.churn}/>
              </div>
            ))}
          </div>
        </Panel>
      </div>
      {/* Bottom row */}
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:12}}>
        <Panel title="Top Prospect Signals" actions={<button onClick={()=>setPage("precrime")} style={{fontSize:9,color:"var(--gold)",background:"none",border:"none",fontFamily:"var(--mono)",cursor:"pointer"}}>VIEW ALL →</button>}>
          <div style={{padding:"10px 14px",display:"flex",flexDirection:"column",gap:10}}>
            {D.prospects.slice(0,4).map(p=>(
              <div key={p.name} style={{display:"flex",gap:10,alignItems:"center"}}>
                <div style={{fontFamily:"var(--mono)",fontSize:17,fontWeight:600,color:p.score>=85?"var(--red)":p.score>=70?"#e07c30":"var(--gold)",flexShrink:0,width:30}}>{p.score}</div>
                <div style={{minWidth:0}}><div style={{fontSize:11,fontWeight:500,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap",color:"var(--t1)"}}>{p.name}</div><div style={{fontSize:9,color:"var(--t3)"}}>{p.need}</div></div>
              </div>
            ))}
          </div>
        </Panel>
        <Panel title="Regulatory Alerts" actions={<button onClick={()=>setPage("reg")} style={{fontSize:9,color:"var(--gold)",background:"none",border:"none",fontFamily:"var(--mono)",cursor:"pointer"}}>VIEW ALL →</button>}>
          <div style={{padding:"10px 14px",display:"flex",flexDirection:"column",gap:8}}>
            {D.regAlerts.slice(0,4).map(r=>(
              <div key={r.id} style={{display:"flex",gap:8,alignItems:"flex-start"}}>
                <Dot c={r.sev==="high"?"var(--red)":r.sev==="medium"?"#e07c30":"#d4a843"} style={{marginTop:4}}/>
                <div><div style={{fontSize:11,fontWeight:500,color:"var(--t1)"}}>{r.src} — {r.pa}</div><div style={{fontSize:9,color:"var(--t3)"}}>{r.affected.length} client(s) mapped · {r.date}</div></div>
              </div>
            ))}
          </div>
        </Panel>
        <Panel title="Competitor Threats" actions={<button onClick={()=>setPage("comp")} style={{fontSize:9,color:"var(--gold)",background:"none",border:"none",fontFamily:"var(--mono)",cursor:"pointer"}}>VIEW ALL →</button>}>
          <div style={{padding:"10px 14px",display:"flex",flexDirection:"column",gap:8}}>
            {D.competitors.map((c,i)=>(
              <div key={i} style={{display:"flex",gap:8,alignItems:"flex-start"}}>
                <Dot c={c.level==="critical"?"var(--red)":c.level==="high"?"#e07c30":"#d4a843"}/>
                <div><div style={{fontSize:11,fontWeight:500,color:"var(--t1)"}}>{c.firm}</div><div style={{fontSize:9,color:"var(--t3)",overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap",maxWidth:140}}>{c.signal.substring(0,48)}…</div></div>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
};

/* ─── CHURN PREDICTOR ───────────────────────────────────────────────────────── */
const ChurnPredictor = ()=>{
  const [sel,setSel]=useState(D.clients.find(c=>c.churn>=60));
  const [brief,setBrief]=useState("");const[loading,setLoading]=useState(false);
  const sigs=D.churnSignals[sel.id]||[];
  const trend=(D.churnSignals[sel.id]?[...Array(7)].map((_,i)=>({m:i+1,r:Math.round(sel.churn*(i+1)/7*(.7+Math.random()*.3))})):D.pipeline.map((p,i)=>({m:i+1,r:Math.min(sel.churn,Math.round(sel.churn*(i+1)/8))})));
  async function gen(){
    setLoading(true);setBrief("");
    try{
      const r={json:async()=>({content:[{text:await import('./api/client.js').then(m=>m.clients.churnBrief(sel.id)).then(d=>d.brief).catch(e=>e.message)}]})}; const _ignore=();
      const d=await r.json();setBrief(d.content?.[0]?.text||"Error.");
    }catch{setBrief("API connection error.");}
    setLoading(false);
  }
  return(
    <div style={{height:"100%",overflowY:"auto",padding:"20px 24px"}}>
      <PageHeader tag="Client Intelligence" title="Silent Client Churn Predictor" sub="Supervised ML scoring detects departure signals in billing rhythm, matter cadence, and communication patterns months before a client moves."/>
      <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:10,marginBottom:16}}>
        <Metric label="Critical Risk" val={D.clients.filter(c=>c.churn>=60).length} sub="≥60 flight risk" accent="red"/>
        <Metric label="Watching" val={D.clients.filter(c=>c.churn>=30&&c.churn<60).length} sub="30–59 risk" accent="gold"/>
        <Metric label="Stable" val={D.clients.filter(c=>c.churn<30).length} sub="<30 risk" accent="green"/>
        <Metric label="Revenue at Risk" val={fmt(D.clients.filter(c=>c.churn>=60).reduce((s,c)=>s+c.rev,0))} sub="flagged clients" accent="red"/>
      </div>
      <div style={{display:"grid",gridTemplateColumns:"260px 1fr",gap:12}}>
        <Panel>
          <div style={{padding:"10px 14px",borderBottom:"1px solid var(--border)",fontFamily:"var(--mono)",fontSize:9,color:"var(--t3)",letterSpacing:".1em",textTransform:"uppercase"}}>Clients — Risk Ranked</div>
          {[...D.clients].sort((a,b)=>b.churn-a.churn).map(c=>(
            <div key={c.id} onClick={()=>{setSel(c);setBrief("");}} style={{padding:"11px 14px",borderBottom:"1px solid var(--border)",cursor:"pointer",background:sel.id===c.id?"var(--elevated)":"transparent",borderLeft:sel.id===c.id?"2px solid var(--gold)":"2px solid transparent",transition:"all .1s"}}>
              <div style={{display:"flex",justifyContent:"space-between",marginBottom:5}}>
                <div style={{fontSize:12,fontWeight:500,color:"var(--t1)"}}>{c.name}</div>
                <span style={{fontSize:8,background:`${riskColor(c.risk)}15`,border:`1px solid ${riskColor(c.risk)}35`,color:riskColor(c.risk),padding:"2px 5px",borderRadius:2,fontFamily:"var(--mono)",height:"fit-content"}}>{c.risk.toUpperCase()}</span>
              </div>
              <div style={{fontSize:9,color:"var(--t3)",marginBottom:5}}>{c.partner} · {fmt(c.rev)}/yr</div>
              <SBar s={c.churn}/>
            </div>
          ))}
        </Panel>
        <div style={{display:"flex",flexDirection:"column",gap:12}}>
          <Panel>
            <div style={{padding:"14px 18px"}}>
              <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:14}}>
                <div>
                  <div style={{fontFamily:"var(--serif)",fontWeight:700,fontSize:18,letterSpacing:"-.02em",color:"var(--t1)",marginBottom:6}}>{sel.name}</div>
                  <div style={{display:"flex",gap:6,flexWrap:"wrap"}}><T ch={sel.industry}/><T ch={sel.region}/>{sel.pgs.map(p=><T key={p} ch={p} color="blue"/>)}</div>
                </div>
                <div style={{textAlign:"right"}}>
                  <div style={{fontFamily:"var(--mono)",fontSize:40,fontWeight:700,color:scoreColor(sel.churn),lineHeight:1}}>{sel.churn}</div>
                  <div style={{fontSize:8,color:"var(--t3)",fontFamily:"var(--mono)"}}>FLIGHT RISK</div>
                </div>
              </div>
              <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:10,paddingTop:12,borderTop:"1px solid var(--border)"}}>
                {[["Active Matter",sel.matter],["Last Contact",`${sel.contact}d ago`],["Annual Revenue",fmt(sel.rev)],["Wallet Share",`${sel.wallet}%`]].map(([l,v])=>(
                  <div key={l}><div style={{fontSize:9,color:"var(--t3)",fontFamily:"var(--mono)",marginBottom:2}}>{l}</div><div style={{fontSize:12,fontWeight:500,fontFamily:"var(--mono)",color:"var(--t1)"}}>{v}</div></div>
                ))}
              </div>
            </div>
          </Panel>
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12}}>
            <Panel title="Risk Trajectory">
              <div style={{padding:"10px 14px"}}>
                <ResponsiveContainer width="100%" height={110}>
                  <LineChart data={trend}>
                    <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false}/>
                    <XAxis dataKey="m" tick={{fill:"var(--t3)",fontSize:9,fontFamily:"'DM Mono'"}} axisLine={false} tickLine={false}/>
                    <YAxis domain={[0,100]} tick={{fill:"var(--t3)",fontSize:9,fontFamily:"'DM Mono'"}} axisLine={false} tickLine={false}/>
                    <Tooltip content={<CTip/>}/>
                    <Line type="monotone" dataKey="r" name="Risk" stroke="var(--red)" strokeWidth={2} dot={false}/>
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Panel>
            <Panel title="Detected Signals">
              <div style={{padding:"10px 14px",display:"flex",flexDirection:"column",gap:7}}>
                {sigs.length?sigs.map((s,i)=>(
                  <div key={i} style={{display:"flex",gap:8,alignItems:"flex-start"}}>
                    <span style={{color:"var(--red)",fontSize:9,marginTop:3,flexShrink:0}}>▸</span>
                    <span style={{fontSize:11,color:"var(--t2)",lineHeight:1.4}}>{s}</span>
                  </div>
                )):<div style={{fontSize:11,color:"var(--t3)"}}>No anomalies detected.</div>}
              </div>
            </Panel>
          </div>
          <Panel title="AI Partner Brief" actions={<div style={{display:"flex",gap:8,alignItems:"center"}}><AiBadge/><OBtn onClick={gen} disabled={loading}>{loading?"…":"Generate Brief"}</OBtn></div>}>
            <div style={{padding:"14px 16px"}}>
              {loading?<Spinner/>:brief?<div style={{fontSize:13,lineHeight:1.75,color:"var(--t2)",borderLeft:"2px solid var(--gold)",paddingLeft:14}}>{brief}</div>:<div style={{fontSize:11,color:"var(--t3)",fontStyle:"italic"}}>Click "Generate Brief" for an AI-powered root cause analysis and immediate action recommendation.</div>}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
};

/* ─── REGULATORY RIPPLE ─────────────────────────────────────────────────────── */
const RegulatoryRipple = ()=>{
  const [sel,setSel]=useState(D.regAlerts[0]);
  const [draft,setDraft]=useState("");const[loading,setLoading]=useState(false);
  const[selClient,setSelClient]=useState(null);
  const affected=D.clients.filter(c=>sel.affected.includes(c.id));
  async function genAlert(client){
    setSelClient(client);setLoading(true);setDraft("");
    try{
      const r={json:async()=>({content:[{text:await import('./api/client.js').then(m=>m.ai.regulatoryAlert({source:sel.src,title:sel.title,date:sel.date,practice_area:sel.pa,client_id:client.id})).then(d=>d.draft).catch(e=>e.message)}]})}; const _ignore2=();
      const d=await r.json();setDraft(d.content?.[0]?.text||"Error.");
    }catch{setDraft("API error.");}
    setLoading(false);
  }
  const sc={high:"var(--red)",medium:"#e07c30",low:"#d4a843"};
  return(
    <div style={{height:"100%",overflowY:"auto",padding:"20px 24px"}}>
      <PageHeader tag="Regulatory Intelligence" title="Regulatory Ripple Engine" sub="Monitors OSC, OSFI, CSA, SEC feeds. Maps new rules to affected clients. Drafts personalized client alerts for partner review — within hours of a rule drop."/>
      <div style={{display:"grid",gridTemplateColumns:"300px 1fr",gap:12}}>
        <Panel>
          <div style={{padding:"10px 14px",borderBottom:"1px solid var(--border)",fontFamily:"var(--mono)",fontSize:9,color:"var(--t3)",letterSpacing:".1em"}}>{D.regAlerts.length} ACTIVE ALERTS</div>
          {D.regAlerts.map(r=>(
            <div key={r.id} onClick={()=>{setSel(r);setDraft("");setSelClient(null);}} style={{padding:"12px 14px",borderBottom:"1px solid var(--border)",cursor:"pointer",background:sel.id===r.id?"var(--elevated)":"transparent",borderLeft:sel.id===r.id?`2px solid ${sc[r.sev]}`:"2px solid transparent"}}>
              <div style={{display:"flex",gap:6,marginBottom:5,alignItems:"center"}}>
                <T ch={r.src} color={r.sev==="high"?"red":r.sev==="medium"?"gold":"default"}/>
                <span style={{fontSize:9,color:"var(--t3)",fontFamily:"var(--mono)"}}>{r.date}</span>
                {r.ready&&<T ch="Ready" color="green"/>}
              </div>
              <div style={{fontSize:11,fontWeight:500,color:"var(--t1)",marginBottom:3}}>{r.pa}</div>
              <div style={{fontSize:10,color:"var(--t3)",overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{r.title}</div>
              <div style={{fontSize:9,color:"var(--t3)",marginTop:4}}>{r.affected.length} client(s) mapped</div>
            </div>
          ))}
        </Panel>
        <div style={{display:"flex",flexDirection:"column",gap:12}}>
          <Panel>
            <div style={{padding:"16px 18px"}}>
              <div style={{display:"flex",gap:8,marginBottom:10,flexWrap:"wrap"}}>
                <T ch={sel.sev.toUpperCase()+" SEVERITY"} color={sel.sev==="high"?"red":sel.sev==="medium"?"gold":"default"}/>
                <T ch={sel.src} color="blue"/>
                <T ch={sel.pa}/>
                <span style={{fontSize:9,color:"var(--t3)",fontFamily:"var(--mono)",marginLeft:"auto",alignSelf:"center"}}>{sel.date}</span>
              </div>
              <h2 style={{fontFamily:"var(--serif)",fontWeight:700,fontSize:16,letterSpacing:"-.01em",lineHeight:1.35,color:"var(--t1)"}}>{sel.title}</h2>
            </div>
          </Panel>
          <Panel title={`Affected Clients — ${affected.length} Mapped`}>
            <div style={{padding:"12px 14px",display:"flex",flexDirection:"column",gap:10}}>
              {affected.map(c=>(
                <div key={c.id} style={{background:"var(--elevated)",border:"1px solid var(--border)",borderRadius:3,padding:"11px 13px"}}>
                  <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:8}}>
                    <div><div style={{fontWeight:600,fontSize:13,color:"var(--t1)"}}>{c.name}</div><div style={{fontSize:10,color:"var(--t3)"}}>{c.partner} · {c.industry}</div></div>
                    <OBtn small onClick={()=>genAlert(c)}>◈ Draft Alert</OBtn>
                  </div>
                  <div style={{display:"flex",gap:5,flexWrap:"wrap"}}>{c.pgs.map(p=><T key={p} ch={p} color="blue"/>)}</div>
                </div>
              ))}
            </div>
          </Panel>
          {(loading||draft)&&(
            <Panel title="AI-Generated Client Alert" actions={<AiBadge/>}>
              <div style={{padding:"14px 16px"}}>
                {selClient&&<div style={{fontSize:10,color:"var(--t3)",fontFamily:"var(--mono)",marginBottom:10}}>FOR: {selClient.name}</div>}
                {loading?<Spinner/>:<div>
                  <div style={{background:"var(--ink)",border:"1px solid var(--border)",borderRadius:3,padding:"14px 16px",marginBottom:10}}>
                    <pre style={{fontFamily:"var(--sans)",fontSize:12,lineHeight:1.75,color:"var(--t2)",whiteSpace:"pre-wrap",margin:0}}>{draft}</pre>
                  </div>
                  <div style={{display:"flex",gap:8}}><OBtn onClick={()=>navigator.clipboard?.writeText(draft)}>Copy Draft</OBtn><OBtn secondary onClick={()=>setDraft("")}>Clear</OBtn></div>
                </div>}
              </div>
            </Panel>
          )}
        </div>
      </div>
    </div>
  );
};

/* ─── PRE-CRIME ACQUISITION ─────────────────────────────────────────────────── */
const PreCrime = ()=>{
  const [sel,setSel]=useState(D.prospects[0]);
  const [strat,setStrat]=useState("");const[loading,setLoading]=useState(false);
  const sc=s=>s>=85?"var(--red)":s>=70?"#e07c30":s>=55?"#d4a843":"#4a8fff";
  async function gen(){
    setLoading(true);setStrat("");
    try{
      const r={json:async()=>({content:[{text:await import('./api/client.js').then(m=>m.ai.prospectOutreach({name:sel.name,score:sel.score,need:sel.need,warmth:sel.warmth,value:sel.value,window:sel.window,signals:sel.signals})).then(d=>d.strategy).catch(e=>e.message)}]})}; const _ignore3=();
      const d=await r.json();setStrat(d.content?.[0]?.text||"Error.");
    }catch{setStrat("API error.");}
    setLoading(false);
  }
  return(
    <div style={{height:"100%",overflowY:"auto",padding:"20px 24px"}}>
      <PageHeader tag="Prospect Intelligence" title="Pre-Crime Acquisition Engine" sub="Scores companies on a Legal Urgency Index based on behavioral patterns that precede legal events — not what's happened, but what's about to."/>
      <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:10,marginBottom:16}}>
        <Metric label="Active Signals" val={D.prospects.length} sub="companies scored" accent="blue"/>
        <Metric label="Urgency ≥ 80" val={D.prospects.filter(p=>p.score>=80).length} sub="call within 48h" accent="red"/>
        <Metric label="Warm Paths" val={D.prospects.filter(p=>p.warmth!=="cold").length} sub="relationship access" accent="green"/>
        <Metric label="Est. Pipeline" val="$3.1M" sub="if all converted" accent="gold"/>
      </div>
      <div style={{display:"grid",gridTemplateColumns:"270px 1fr",gap:12}}>
        <Panel>
          <div style={{padding:"10px 14px",borderBottom:"1px solid var(--border)",fontFamily:"var(--mono)",fontSize:9,color:"var(--t3)",letterSpacing:".1em"}}>SORTED BY URGENCY INDEX</div>
          {[...D.prospects].sort((a,b)=>b.score-a.score).map(p=>(
            <div key={p.name} onClick={()=>{setSel(p);setStrat("");}} style={{padding:"12px 14px",borderBottom:"1px solid var(--border)",cursor:"pointer",background:sel.name===p.name?"var(--elevated)":"transparent",borderLeft:sel.name===p.name?"2px solid var(--gold)":"2px solid transparent"}}>
              <div style={{display:"flex",justifyContent:"space-between",marginBottom:5}}>
                <div style={{fontSize:12,fontWeight:500,color:"var(--t1)"}}>{p.name}</div>
                <div style={{fontFamily:"var(--mono)",fontSize:18,fontWeight:700,color:sc(p.score),lineHeight:1}}>{p.score}</div>
              </div>
              <div style={{fontSize:10,color:"var(--t3)",marginBottom:5}}>{p.need}</div>
              <div style={{display:"flex",gap:5}}><T ch={p.warmth.toUpperCase()} color={p.warmth==="warm"?"green":p.warmth==="lukewarm"?"gold":"blue"}/><T ch={p.window}/></div>
            </div>
          ))}
        </Panel>
        <div style={{display:"flex",flexDirection:"column",gap:12}}>
          <Panel>
            <div style={{padding:"16px 18px"}}>
              <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:12}}>
                <div>
                  <div style={{fontFamily:"var(--serif)",fontWeight:700,fontSize:20,letterSpacing:"-.02em",color:"var(--t1)",marginBottom:6}}>{sel.name}</div>
                  <div style={{display:"flex",gap:6,flexWrap:"wrap"}}>
                    <T ch={sel.need} color="gold"/>
                    <T ch={sel.warmth.toUpperCase()} color={sel.warmth==="warm"?"green":sel.warmth==="lukewarm"?"gold":"blue"}/>
                    <T ch={sel.value}/>
                    <T ch={`Window: ${sel.window}`}/>
                  </div>
                </div>
                <div style={{textAlign:"right"}}>
                  <div style={{fontFamily:"var(--mono)",fontSize:44,fontWeight:700,color:sc(sel.score),lineHeight:1}}>{sel.score}</div>
                  <div style={{fontSize:8,color:"var(--t3)",fontFamily:"var(--mono)"}}>LEGAL URGENCY INDEX</div>
                </div>
              </div>
            </div>
          </Panel>
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12}}>
            <Panel title="Pre-Legal Signals Detected">
              <div style={{padding:"10px 14px",display:"flex",flexDirection:"column",gap:8}}>
                {sel.signals.map((s,i)=>(
                  <div key={i} style={{display:"flex",gap:8,alignItems:"flex-start",padding:"7px 10px",background:"var(--elevated)",borderRadius:3,border:"1px solid var(--border)"}}>
                    <span style={{color:"var(--gold)",fontSize:9,marginTop:3,flexShrink:0}}>◉</span>
                    <span style={{fontSize:11,color:"var(--t2)",lineHeight:1.4}}>{s}</span>
                  </div>
                ))}
              </div>
            </Panel>
            <Panel title="AI Outreach Strategy" actions={<div style={{display:"flex",gap:6}}><AiBadge/><OBtn small onClick={gen} disabled={loading}>{loading?"…":"Generate"}</OBtn></div>}>
              <div style={{padding:"10px 14px"}}>
                {loading?<Spinner/>:strat?<div style={{fontSize:12,lineHeight:1.7,color:"var(--t2)",borderLeft:"2px solid var(--gold)",paddingLeft:12}}>{strat}</div>:<div style={{fontSize:11,color:"var(--t3)",fontStyle:"italic"}}>Generate an AI outreach strategy — opening line, urgency framing, first-call agenda.</div>}
              </div>
            </Panel>
          </div>
        </div>
      </div>
    </div>
  );
};

/* ─── WALLET SHARE ──────────────────────────────────────────────────────────── */
const WalletShare = ()=>{
  const [sel,setSel]=useState(D.clients[0]);
  const barData=D.clients.map(c=>({name:c.name.split(" ")[0],cap:c.wallet,uncap:100-c.wallet}));
  const totalSpend=D.clients.reduce((s,c)=>s+c.spend,0);
  const totalRev=D.clients.reduce((s,c)=>s+c.rev,0);
  const whitespace=[
    {area:"Employment Law",clients:D.clients.filter(c=>!c.pgs.includes("Employment")),est:3200000},
    {area:"Tax Advisory",clients:D.clients.filter(c=>!c.pgs.includes("Tax")),est:4800000},
    {area:"ESG Advisory",clients:D.clients.filter(c=>!c.pgs.includes("ESG")),est:1900000},
    {area:"Restructuring",clients:D.clients.filter(c=>!c.pgs.includes("Restructuring")),est:2700000},
    {area:"IP Licensing",clients:D.clients.filter(c=>!c.pgs.includes("IP")),est:2100000},
  ];
  return(
    <div style={{height:"100%",overflowY:"auto",padding:"20px 24px"}}>
      <PageHeader tag="Revenue Intelligence" title="Wallet Share Engine" sub="Estimates total outside counsel spend per client and computes your capture rate. Surfaces whitespace — practice areas clients spend on where you have zero active matters."/>
      <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:10,marginBottom:16}}>
        <Metric label="Total Client Spend" val={fmt(totalSpend)} sub="est. across clients" accent="blue"/>
        <Metric label="Firm Revenue" val={fmt(totalRev)} sub="captured" accent="green"/>
        <Metric label="Uncaptured" val={fmt(totalSpend-totalRev)} sub="at other firms" accent="red"/>
        <Metric label="Avg Wallet Share" val={`${Math.round(D.clients.reduce((s,c)=>s+c.wallet,0)/D.clients.length)}%`} sub="of client spend" accent="gold"/>
      </div>
      <div style={{display:"grid",gridTemplateColumns:"1fr 300px",gap:12,marginBottom:12}}>
        <Panel title="Wallet Share by Client">
          <div style={{padding:"14px 16px"}}>
            <div style={{display:"flex",gap:12,marginBottom:10}}>
              {[{c:"var(--green)",l:"Captured"},{c:"var(--border2)",l:"At Other Firms"}].map(i=>(
                <div key={i.l} style={{display:"flex",gap:5,alignItems:"center"}}>
                  <div style={{width:9,height:9,background:i.c,borderRadius:2}}/>
                  <span style={{fontSize:9,color:"var(--t3)",fontFamily:"var(--mono)"}}>{i.l}</span>
                </div>
              ))}
            </div>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={barData} onClick={d=>d?.activeLabel&&setSel(D.clients.find(c=>c.name.startsWith(d.activeLabel)))}>
                <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false}/>
                <XAxis dataKey="name" tick={{fill:"var(--t3)",fontSize:9,fontFamily:"'DM Mono'"}} axisLine={false} tickLine={false}/>
                <YAxis domain={[0,100]} tickFormatter={v=>`${v}%`} tick={{fill:"var(--t3)",fontSize:9,fontFamily:"'DM Mono'"}} axisLine={false} tickLine={false}/>
                <Tooltip content={<CTip/>}/>
                <Bar dataKey="cap" name="Captured%" stackId="a" fill="var(--green)" radius={[0,0,0,0]}/>
                <Bar dataKey="uncap" name="Uncaptured%" stackId="a" fill="rgba(26,38,64,.8)" radius={[2,2,0,0]}/>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
        <Panel title="Client Snapshot">
          <div style={{padding:"14px 16px"}}>
            <div style={{fontWeight:600,fontSize:13,color:"var(--t1)",marginBottom:3}}>{sel.name}</div>
            <div style={{fontSize:10,color:"var(--t3)",marginBottom:12}}>{sel.industry} · {sel.region}</div>
            <div style={{background:"rgba(61,186,122,.06)",border:"1px solid rgba(61,186,122,.2)",borderRadius:3,padding:"11px 12px",marginBottom:10}}>
              {[["Total Legal Spend",fmt(sel.spend),"var(--t1)"],["Captured by Firm",fmt(sel.rev),"var(--green)"],["At Other Firms",fmt(sel.spend-sel.rev),"var(--red)"]].map(([l,v,c])=>(
                <div key={l} style={{display:"flex",justifyContent:"space-between",marginBottom:5}}>
                  <span style={{fontSize:10,color:"var(--t3)",fontFamily:"var(--mono)"}}>{l}</span>
                  <span style={{fontSize:12,fontWeight:600,color:c,fontFamily:"var(--mono)"}}>{v}</span>
                </div>
              ))}
              <div style={{paddingTop:8,borderTop:"1px solid rgba(61,186,122,.15)"}}>
                <SBar s={sel.wallet} color="green"/>
                <div style={{fontSize:9,color:"var(--t3)",marginTop:3}}>Wallet Share: {sel.wallet}%</div>
              </div>
            </div>
            <div style={{fontSize:9,color:"var(--t3)",fontFamily:"var(--mono)",marginBottom:5}}>PRACTICE GROUPS</div>
            <div style={{display:"flex",gap:4,flexWrap:"wrap"}}>{sel.pgs.map(p=><T key={p} ch={p} color="blue"/>)}</div>
          </div>
        </Panel>
      </div>
      <Panel title="Practice Area Whitespace Map — Where Clients Are Spending Elsewhere">
        <div style={{padding:"14px 16px",display:"grid",gridTemplateColumns:"repeat(5,1fr)",gap:10}}>
          {whitespace.map(w=>(
            <div key={w.area} style={{background:"var(--elevated)",border:"1px solid var(--border)",borderRadius:3,padding:"12px 12px"}}>
              <div style={{fontWeight:500,fontSize:12,color:"var(--t1)",marginBottom:4}}>{w.area}</div>
              <div style={{fontFamily:"var(--mono)",fontSize:18,fontWeight:700,color:"var(--gold)",marginBottom:4}}>{fmt(w.est)}</div>
              <div style={{fontSize:9,color:"var(--t3)",marginBottom:6}}>est. annual spend</div>
              <div style={{fontSize:9,color:"var(--t2)"}}>{w.clients.length} client(s) with zero matters</div>
              {w.clients.slice(0,2).map(c=><div key={c.id} style={{fontSize:9,color:"var(--t3)",marginTop:3}}>· {c.name.split(" ")[0]}</div>)}
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
};

/* ─── COMPETITIVE INTEL ─────────────────────────────────────────────────────── */
const CompIntel = ()=>{
  const conflicts=[
    {co:"Arctis Mining Corp",sit:"Being sued by Apple subsidiary",blocked:["Osler (Apple retainer)","Davies (Apple M&A)"],status:"CLEAR — No Apple relationship",adv:"Only major firm eligible to pitch"},
    {co:"Pinnacle Health Systems",sit:"OSFI regulatory investigation",blocked:["Stikeman (regulator informal retainer)"],status:"CLEAR",adv:"2 of 4 top rivals conflicted out"},
  ];
  return(
    <div style={{height:"100%",overflowY:"auto",padding:"20px 24px"}}>
      <PageHeader tag="Competitive Intelligence" title="Competitor Radar" sub="Real-time monitoring of rival firm lateral hires, practice expansions, event presence, alumni threats, and conflict-of-interest arbitrage windows."/>
      <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:10,marginBottom:16}}>
        <Metric label="Active Threats" val={D.competitors.filter(c=>c.level==="critical"||c.level==="high").length} sub="critical + high" accent="red"/>
        <Metric label="Clients Targeted" val={new Set(D.competitors.flatMap(c=>c.clients)).size} sub="by competitors" accent="gold"/>
        <Metric label="Conflict Openings" val={conflicts.length} sub="rivals blocked" accent="green"/>
        <Metric label="Firms Monitored" val={new Set(D.competitors.map(c=>c.firm)).size} sub="on radar" accent="blue"/>
      </div>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12}}>
        <div>
          <div style={{fontFamily:"var(--mono)",fontSize:9,color:"var(--t2)",letterSpacing:".1em",textTransform:"uppercase",marginBottom:8}}>Live Threat Feed</div>
          <div style={{display:"flex",flexDirection:"column",gap:10}}>
            {D.competitors.map((c,i)=>{
              const lc={critical:"var(--red)",high:"#e07c30",medium:"#d4a843",low:"var(--green)"};
              return(
                <div key={i} style={{background:c.level==="critical"?"rgba(224,82,82,.05)":c.level==="high"?"rgba(224,124,48,.04)":"rgba(212,168,67,.04)",border:`1px solid ${lc[c.level]}25`,borderLeft:`3px solid ${lc[c.level]}`,borderRadius:3,padding:"13px 15px"}}>
                  <div style={{display:"flex",justifyContent:"space-between",marginBottom:7}}>
                    <div style={{fontWeight:600,fontSize:13,color:"var(--t1)"}}>{c.firm}</div>
                    <div style={{display:"flex",gap:5}}>
                      <T ch={c.cat}/>
                      <span style={{fontSize:8,fontFamily:"var(--mono)",color:lc[c.level],background:`${lc[c.level]}18`,border:`1px solid ${lc[c.level]}35`,padding:"2px 6px",borderRadius:2}}>{c.level.toUpperCase()}</span>
                    </div>
                  </div>
                  <div style={{fontSize:12,color:"var(--t2)",lineHeight:1.5,marginBottom:7}}>{c.signal}</div>
                  <div style={{display:"flex",gap:6,alignItems:"center"}}>
                    <span style={{fontSize:9,color:"var(--t3)",fontFamily:"var(--mono)"}}>{c.date}</span>
                    <span style={{fontSize:9,color:"var(--t3)"}}>·</span>
                    {c.clients.map(cl=><T key={cl} ch={cl.split(" ")[0]} color="gold"/>)}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
        <div>
          <div style={{fontFamily:"var(--mono)",fontSize:9,color:"var(--t2)",letterSpacing:".1em",textTransform:"uppercase",marginBottom:8}}>Conflict Arbitrage — Clear Windows</div>
          <div style={{display:"flex",flexDirection:"column",gap:10,marginBottom:14}}>
            {conflicts.map((c,i)=>(
              <div key={i} className="panel" style={{background:"var(--card)",border:"1px solid var(--border)",borderRadius:4,padding:"13px 15px"}}>
                <div style={{fontWeight:600,fontSize:13,color:"var(--t1)",marginBottom:3}}>{c.co}</div>
                <div style={{fontSize:11,color:"var(--t3)",marginBottom:9}}>{c.sit}</div>
                <div style={{marginBottom:9}}>
                  <div style={{fontSize:9,color:"var(--t3)",fontFamily:"var(--mono)",marginBottom:5}}>CONFLICTED RIVALS</div>
                  {c.blocked.map((f,j)=><div key={j} style={{display:"flex",gap:6,alignItems:"center",marginBottom:3}}><span style={{color:"var(--red)",fontSize:10}}>✕</span><span style={{fontSize:11,color:"var(--t2)"}}>{f}</span></div>)}
                </div>
                <div style={{background:"rgba(61,186,122,.08)",border:"1px solid rgba(61,186,122,.25)",borderRadius:3,padding:"9px 11px"}}>
                  <div style={{fontSize:9,color:"var(--green)",fontFamily:"var(--mono)",marginBottom:3}}>OUR POSITION</div>
                  <div style={{fontSize:12,fontWeight:600,color:"var(--green)",marginBottom:3}}>{c.status}</div>
                  <div style={{fontSize:11,color:"var(--t2)"}}>{c.adv}</div>
                </div>
              </div>
            ))}
          </div>
          <Panel title="Threat Ranking">
            {[{f:"Davies Ward Phillips",n:2,s:92},{f:"Osler Hoskin",n:2,s:78},{f:"Stikeman Elliott",n:1,s:61},{f:"Blake Cassels",n:1,s:44}].map((f,i)=>(
              <div key={i} style={{display:"grid",gridTemplateColumns:"1fr 40px 20px",gap:10,alignItems:"center",padding:"9px 14px",borderBottom:"1px solid var(--border)"}}>
                <div><div style={{fontSize:12,fontWeight:500,color:"var(--t1)"}}>{f.f}</div><div style={{fontSize:9,color:"var(--t3)"}}>{f.n} active signal(s)</div></div>
                <div style={{fontFamily:"var(--mono)",fontSize:14,fontWeight:700,color:f.s>=75?"var(--red)":f.s>=50?"#e07c30":"var(--gold)",textAlign:"center"}}>{f.s}</div>
                <Dot c={f.s>=75?"var(--red)":f.s>=50?"#e07c30":"var(--gold)"}/>
              </div>
            ))}
          </Panel>
        </div>
      </div>
    </div>
  );
};

/* ─── ALUMNI ACTIVATOR ──────────────────────────────────────────────────────── */
const AlumniActivator = ()=>{
  const [sel,setSel]=useState(D.alumni.find(a=>a.active));
  const [msg,setMsg]=useState("");const[loading,setLoading]=useState(false);
  async function gen(){
    setLoading(true);setMsg("");
    try{
      const r={json:async()=>({content:[{text:await import('./api/client.js').then(m=>m.ai.alumniMessage(sel.id)).then(d=>d.message).catch(e=>e.message)}]})}; const _ignore4=();
      const d=await r.json();setMsg(d.content?.[0]?.text||"Error.");
    }catch{setMsg("API error.");}
    setLoading(false);
  }
  return(
    <div style={{height:"100%",overflowY:"auto",padding:"20px 24px"}}>
      <PageHeader tag="Network Intelligence" title="Alumni Sleeper Cell Activator" sub="Maps every former associate to their in-house role. Detects legal triggers at their companies. Auto-drafts warm personal outreach — invisible pipeline activation through trusted relationships."/>
      <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:10,marginBottom:16}}>
        <Metric label="Alumni Tracked" val={D.alumni.length} sub="former associates" accent="blue"/>
        <Metric label="Active Triggers" val={D.alumni.filter(a=>a.active).length} sub="legal events detected" accent="red"/>
        <Metric label="Avg Warmth" val={Math.round(D.alumni.reduce((s,a)=>s+a.warmth,0)/D.alumni.length)} sub="relationship score" accent="gold"/>
        <Metric label="Est. Pipeline" val="$1.2M" sub="from triggered alumni" accent="green"/>
      </div>
      <div style={{display:"grid",gridTemplateColumns:"260px 1fr",gap:12}}>
        <Panel>
          {D.alumni.map(a=>(
            <div key={a.name} onClick={()=>{setSel(a);setMsg("");}} style={{padding:"12px 14px",borderBottom:"1px solid var(--border)",cursor:"pointer",background:sel.name===a.name?"var(--elevated)":"transparent",borderLeft:sel.name===a.name?"2px solid var(--gold)":a.active?"2px solid var(--red)":"2px solid transparent"}}>
              <div style={{display:"flex",justifyContent:"space-between",marginBottom:3}}>
                <div style={{fontSize:12,fontWeight:500,color:"var(--t1)"}}>{a.name}</div>
                <div style={{fontFamily:"var(--mono)",fontSize:13,fontWeight:600,color:warmthColor(a.warmth)}}>{a.warmth}</div>
              </div>
              <div style={{fontSize:10,color:"var(--t3)",marginBottom:3}}>{a.role}</div>
              <div style={{fontSize:10,color:"var(--gold)",marginBottom:5}}>{a.company}</div>
              {a.active&&<div style={{background:"rgba(224,82,82,.08)",border:"1px solid rgba(224,82,82,.3)",borderRadius:2,padding:"3px 7px"}}><div style={{fontSize:8,color:"var(--red)",fontFamily:"var(--mono)",letterSpacing:".06em"}}>⚡ TRIGGER ACTIVE</div></div>}
            </div>
          ))}
        </Panel>
        <div style={{display:"flex",flexDirection:"column",gap:12}}>
          <Panel>
            <div style={{padding:"16px 18px"}}>
              <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:12}}>
                <div>
                  <div style={{fontFamily:"var(--serif)",fontWeight:700,fontSize:18,letterSpacing:"-.02em",color:"var(--t1)",marginBottom:5}}>{sel.name}</div>
                  <div style={{fontSize:12,color:"var(--t3)",marginBottom:8}}>{sel.role} · {sel.company}</div>
                  <div style={{display:"flex",gap:6,flexWrap:"wrap"}}>
                    <T ch={`Left ${sel.left}`}/>
                    <T ch={`Mentored by ${sel.mentor}`}/>
                    <T ch={`${2025-sel.left} yrs ago`}/>
                  </div>
                </div>
                <div style={{textAlign:"right"}}>
                  <div style={{fontFamily:"var(--mono)",fontSize:38,fontWeight:700,color:warmthColor(sel.warmth),lineHeight:1}}>{sel.warmth}</div>
                  <div style={{fontSize:8,color:"var(--t3)",fontFamily:"var(--mono)"}}>WARMTH SCORE</div>
                </div>
              </div>
            </div>
          </Panel>
          {sel.active&&(
            <div style={{background:"rgba(224,82,82,.04)",border:"1px solid rgba(224,82,82,.25)",borderRadius:4,padding:"14px 16px"}}>
              <div style={{display:"flex",gap:8,alignItems:"center",marginBottom:8}}><span style={{fontSize:14}}>⚡</span><span style={{fontFamily:"var(--mono)",fontSize:9,color:"var(--red)",letterSpacing:".1em",textTransform:"uppercase"}}>Legal Trigger Detected</span></div>
              <div style={{fontSize:13,color:"var(--t1)",fontWeight:500,marginBottom:5}}>{sel.trigger}</div>
              <div style={{fontSize:11,color:"var(--t3)"}}>{sel.mentor} should reach out within 48 hours via {sel.name.split(" ")[0]}'s personal connection.</div>
            </div>
          )}
          <Panel title="AI Message — From Partner to Former Associate" actions={<div style={{display:"flex",gap:6}}><AiBadge/><OBtn small onClick={gen} disabled={loading||!sel.active}>{loading?"…":"Draft Message"}</OBtn></div>}>
            <div style={{padding:"12px 14px"}}>
              {!sel.active&&!msg&&<div style={{fontSize:11,color:"var(--t3)",fontStyle:"italic"}}>No active trigger detected. Message drafting requires a legal trigger at their company.</div>}
              {loading?<Spinner/>:msg&&(
                <div>
                  <div style={{background:"var(--ink)",border:"1px solid var(--border)",borderRadius:3,padding:"13px 15px",marginBottom:10}}>
                    <pre style={{fontFamily:"var(--sans)",fontSize:12,lineHeight:1.8,color:"var(--t2)",whiteSpace:"pre-wrap",margin:0}}>{msg}</pre>
                  </div>
                  <div style={{display:"flex",gap:8}}><OBtn onClick={()=>navigator.clipboard?.writeText(msg)}>Copy</OBtn><OBtn secondary onClick={gen}>Regenerate</OBtn></div>
                </div>
              )}
              {!loading&&!msg&&sel.active&&<div style={{fontSize:11,color:"var(--t3)",fontStyle:"italic"}}>Click "Draft Message" to generate a warm personal outreach note from {sel.mentor} to {sel.name.split(" ")[0]}.</div>}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
};

/* ─── GC PROFILER ───────────────────────────────────────────────────────────── */
const GCProfiler = ()=>{
  const [input,setInput]=useState("");const[co,setCo]=useState("");
  const [profile,setProfile]=useState(null);const[loading,setLoading]=useState(false);
  const TDial = ({label,score,invert})=>{
    const eff=invert?100-score:score;
    const c=eff>=70?"var(--green)":eff>=40?"var(--gold)":"var(--red)";
    const circ=2*Math.PI*22;
    return(
      <div style={{textAlign:"center"}}>
        <div style={{position:"relative",width:58,height:58,margin:"0 auto 5px"}}>
          <svg width="58" height="58" style={{transform:"rotate(-90deg)"}}>
            <circle cx="29" cy="29" r="22" fill="none" stroke="var(--border)" strokeWidth="4"/>
            <circle cx="29" cy="29" r="22" fill="none" stroke={c} strokeWidth="4" strokeDasharray={`${eff/100*circ} ${circ}`} strokeLinecap="round"/>
          </svg>
          <div style={{position:"absolute",inset:0,display:"flex",alignItems:"center",justifyContent:"center",fontFamily:"var(--mono)",fontSize:13,fontWeight:600,color:c}}>{eff}</div>
        </div>
        <div style={{fontSize:8,color:"var(--t3)",fontFamily:"var(--mono)",letterSpacing:".05em"}}>{label}</div>
      </div>
    );
  };
  async function gen(){
    if(!input.trim())return;
    setLoading(true);setProfile(null);
    try{
      const r={json:async()=>({content:[{text:await import('./api/client.js').then(m=>m.ai.gcProfile({company:co||'Unknown',information:input})).then(d=>JSON.stringify(d.profile)).catch(e=>'{}')}]})}; const _ignore5=();
      const d=await r.json();
      const txt=(d.content?.[0]?.text||"{}").replace(/```json|```/g,"").trim();
      setProfile(JSON.parse(txt));
    }catch(e){setProfile({name:"Parse Error",brief:"Could not parse AI response. Try again.",key_concerns:[],pitch_hooks:[],credibility:0,reliability:0,intimacy:0,self_orientation:0,trust_score:0});}
    setLoading(false);
  }
  return(
    <div style={{height:"100%",overflowY:"auto",padding:"20px 24px"}}>
      <PageHeader tag="Relationship Intelligence" title="GC Psychographic Profiler" sub="Paste any public information about a GC. ORACLE builds a complete decision-making profile — risk tolerance, fee sensitivity, pitch hooks, and a pre-meeting intelligence brief — in seconds."/>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12}}>
        <Panel title="Profile Input" actions={<AiBadge/>}>
          <div style={{padding:"14px 16px"}}>
            <div style={{marginBottom:10}}>
              <label style={{fontSize:9,color:"var(--t3)",fontFamily:"var(--mono)",display:"block",marginBottom:5,letterSpacing:".08em"}}>COMPANY NAME</label>
              <input style={{width:"100%",background:"var(--ink)",border:"1px solid var(--border2)",color:"var(--t1)",padding:"7px 10px",borderRadius:3,fontSize:12,outline:"none"}} placeholder="e.g. Pinnacle Health Systems" value={co} onChange={e=>setCo(e.target.value)}/>
            </div>
            <div style={{marginBottom:14}}>
              <label style={{fontSize:9,color:"var(--t3)",fontFamily:"var(--mono)",display:"block",marginBottom:5,letterSpacing:".08em"}}>PUBLIC INFORMATION (LinkedIn bio, speeches, interviews, news)</label>
              <textarea style={{width:"100%",background:"var(--ink)",border:"1px solid var(--border2)",color:"var(--t1)",padding:"9px 10px",borderRadius:3,fontSize:12,outline:"none",resize:"none",lineHeight:1.6}} rows={10} placeholder="Paste any publicly available information about the GC here — LinkedIn About section, quotes from interviews, panel bios, conference speech topics, published articles, news mentions, regulatory testimony..." value={input} onChange={e=>setInput(e.target.value)}/>
            </div>
            <OBtn onClick={gen} disabled={loading||!input.trim()} style={{width:"100%"}}>
              {loading?"Analyzing Public Signals…":"◈ Generate Psychographic Profile"}
            </OBtn>
          </div>
        </Panel>
        <div>
          {loading&&<div style={{padding:"40px 20px",display:"flex",justifyContent:"center",background:"var(--card)",border:"1px solid var(--border)",borderRadius:4}}><Spinner/></div>}
          {profile&&!loading&&(
            <div style={{display:"flex",flexDirection:"column",gap:12}}>
              <Panel>
                <div style={{padding:"16px 18px"}}>
                  <div style={{fontFamily:"var(--serif)",fontWeight:700,fontSize:18,letterSpacing:"-.02em",color:"var(--t1)",marginBottom:3}}>{profile.name||"GC Profile"}</div>
                  <div style={{fontSize:11,color:"var(--t3)",marginBottom:12}}>{profile.title||"General Counsel"} · {co}</div>
                  {profile.brief&&<div style={{background:"rgba(212,168,67,.05)",border:"1px solid rgba(212,168,67,.2)",borderRadius:3,padding:"10px 12px",marginBottom:14}}>
                    <div style={{fontSize:9,color:"var(--gold)",fontFamily:"var(--mono)",marginBottom:5}}>PRE-MEETING BRIEF</div>
                    <div style={{fontSize:12,lineHeight:1.65,color:"var(--t2)"}}>{profile.brief}</div>
                  </div>}
                  <div style={{display:"flex",justifyContent:"space-around",paddingTop:12,borderTop:"1px solid var(--border)"}}>
                    <TDial label="CREDIBILITY" score={profile.credibility||0}/>
                    <TDial label="RELIABILITY" score={profile.reliability||0}/>
                    <TDial label="INTIMACY" score={profile.intimacy||0}/>
                    <TDial label="SELF-ORIENT" score={profile.self_orientation||0} invert/>
                    <TDial label="TRUST SCORE" score={profile.trust_score||0}/>
                  </div>
                </div>
              </Panel>
              {(profile.key_concerns?.length||profile.pitch_hooks?.length)&&(
                <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12}}>
                  <Panel title="Key Concerns">
                    <div style={{padding:"10px 14px"}}>
                      {(profile.key_concerns||[]).map((c,i)=>(
                        <div key={i} style={{display:"flex",gap:7,marginBottom:8}}><span style={{color:"var(--red)",fontSize:9,marginTop:3}}>▸</span><span style={{fontSize:11,color:"var(--t2)",lineHeight:1.4}}>{c}</span></div>
                      ))}
                    </div>
                  </Panel>
                  <Panel title="Pitch Hooks">
                    <div style={{padding:"10px 14px"}}>
                      {(profile.pitch_hooks||[]).map((h,i)=>(
                        <div key={i} style={{display:"flex",gap:7,marginBottom:8}}><span style={{color:"var(--green)",fontSize:9,marginTop:3}}>◉</span><span style={{fontSize:11,color:"var(--t2)",lineHeight:1.4}}>{h}</span></div>
                      ))}
                    </div>
                  </Panel>
                </div>
              )}
            </div>
          )}
          {!profile&&!loading&&(
            <div style={{background:"var(--card)",border:"1px solid var(--border)",borderRadius:4,padding:"50px 30px",textAlign:"center",color:"var(--t3)"}}>
              <div style={{fontSize:28,marginBottom:12}}>◈</div>
              <div style={{fontSize:12,lineHeight:1.7}}>Paste any public information about a GC — LinkedIn, speeches, interviews, news — and ORACLE builds a complete psychographic profile including decision style, fee sensitivity, communication preferences, trust scores, and a pre-meeting brief.</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

/* ─── MANDATE FORMATION ─────────────────────────────────────────────────────── */
const MandateFormation = ()=>{
  const sigs=[
    {co:"Arctis Mining Corp",conf:94,type:"M&A Advisory + Securities",val:"$680K",window:"14 days",forming:true,layers:[
      {l:"M&A Dark Signal",t:"Options volume 340% above 90-day avg",s:91,c:"var(--purple)"},
      {l:"Reg/Compliance",t:"OSC sector enforcement sweep forming",s:84,c:"var(--red)"},
      {l:"Human Capital",t:"Senior compliance officer departed 45d",s:78,c:"#e07c30"},
      {l:"Behavioral",t:"CEO earnings NLP: hedged language pattern",s:66,c:"var(--cyan)"},
      {l:"Corp/Structural",t:"Board special committee — unscheduled",s:73,c:"var(--gold)"},
    ]},
    {co:"Westbrook Digital Corp",conf:88,type:"Privacy / Cybersecurity / Regulatory",val:"$290K",window:"48 hours",forming:true,layers:[
      {l:"Dark Web",t:"Domain credentials on BreachForums 03:14 AM",s:99,c:"var(--red)"},
      {l:"Human Capital",t:"CISO role posted same day as breach signal",s:88,c:"#e07c30"},
      {l:"Behavioral",t:"Privacy policy page deleted from website",s:75,c:"var(--cyan)"},
      {l:"Hiring Velocity",t:"IT security hiring +200% past 60 days",s:82,c:"var(--green)"},
    ]},
    {co:"Vantage Rail Corp",conf:62,type:"Regulatory / Employment",val:"$180K",window:"4–6 wks",forming:false,layers:[
      {l:"Regulatory",t:"Transport Canada audit notice filed",s:72,c:"var(--red)"},
      {l:"Litigation",t:"2 new small claims filed this quarter",s:55,c:"#e07c30"},
      {l:"Human Capital",t:"HR Director departed without announcement",s:61,c:"var(--gold)"},
    ]},
  ];
  const [sel,setSel]=useState(sigs[0]);
  const [brief,setBrief]=useState("");const[loading,setLoading]=useState(false);
  async function gen(){
    setLoading(true);setBrief("");
    try{
      const r={json:async()=>({content:[{text:await import('./api/client.js').then(m=>m.ai.mandateBrief({company:sel.co,confidence:sel.conf,practice:sel.type,value:sel.val,window:sel.window,signals:sel.layers.map(l=>({layer:l.l,text:l.t,score:l.s}))})).then(d=>d.brief).catch(e=>e.message)}]})}; const _ignore6=();
      const d=await r.json();setBrief(d.content?.[0]?.text||"Error.");
    }catch{setBrief("API error.");}
    setLoading(false);
  }
  const cc=c=>c>=85?"var(--red)":c>=70?"#e07c30":"var(--gold)";
  return(
    <div style={{height:"100%",overflowY:"auto",padding:"20px 24px"}}>
      <PageHeader tag="Predictive Intelligence" title="Mandate Pre-Formation Detector" sub="Detects the moment a legal mandate is forming — before the GC calls any firm. Six intelligence layers converge into a single tactical action brief."/>
      <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:10,marginBottom:16}}>
        <Metric label="Formation Alerts" val={sigs.filter(s=>s.forming).length} sub="high-confidence" accent="red"/>
        <Metric label="Avg Confidence" val={`${Math.round(sigs.reduce((s,m)=>s+m.conf,0)/sigs.length)}%`} sub="signal accuracy" accent="gold"/>
        <Metric label="Est. Pipeline" val="$1.2M" sub="if all engaged" accent="green"/>
        <Metric label="Avg Days to Window" val="22" sub="historical accuracy" accent="blue"/>
      </div>
      <div style={{display:"grid",gridTemplateColumns:"260px 1fr",gap:12}}>
        <Panel>
          {sigs.map((s,i)=>(
            <div key={i} onClick={()=>{setSel(s);setBrief("");}} style={{padding:"12px 14px",borderBottom:"1px solid var(--border)",cursor:"pointer",background:sel.co===s.co?"var(--elevated)":"transparent",borderLeft:sel.co===s.co?"2px solid var(--gold)":s.forming?"2px solid var(--red)":"2px solid transparent"}}>
              <div style={{display:"flex",justifyContent:"space-between",marginBottom:5}}>
                <div style={{fontSize:12,fontWeight:500,color:"var(--t1)"}}>{s.co}</div>
                <div style={{fontFamily:"var(--mono)",fontSize:18,fontWeight:700,color:cc(s.conf),lineHeight:1}}>{s.conf}%</div>
              </div>
              <div style={{fontSize:10,color:"var(--t3)",marginBottom:5}}>{s.type}</div>
              <div style={{display:"flex",gap:5}}>{s.forming&&<T ch="⚡ FORMING" color="red"/>}<T ch={s.window}/></div>
            </div>
          ))}
        </Panel>
        <div style={{display:"flex",flexDirection:"column",gap:12}}>
          <Panel>
            <div style={{padding:"16px 18px"}}>
              <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:12}}>
                <div>
                  <div style={{fontFamily:"var(--serif)",fontWeight:700,fontSize:20,letterSpacing:"-.02em",color:"var(--t1)",marginBottom:6}}>{sel.co}</div>
                  <div style={{display:"flex",gap:6,flexWrap:"wrap"}}>
                    {sel.forming&&<T ch="⚡ MANDATE FORMING" color="red"/>}
                    <T ch={sel.type} color="gold"/>
                    <T ch={sel.val}/>
                    <T ch={`Window: ${sel.window}`}/>
                  </div>
                </div>
                <div style={{textAlign:"right"}}>
                  <div style={{fontFamily:"var(--mono)",fontSize:44,fontWeight:700,color:cc(sel.conf),lineHeight:1}}>{sel.conf}%</div>
                  <div style={{fontSize:8,color:"var(--t3)",fontFamily:"var(--mono)"}}>FORMATION CONFIDENCE</div>
                </div>
              </div>
              <div style={{paddingTop:12,borderTop:"1px solid var(--border)"}}>
                <div style={{fontSize:9,color:"var(--t3)",fontFamily:"var(--mono)",letterSpacing:".1em",marginBottom:10}}>SIGNAL CONVERGENCE — {sel.layers.length} LAYERS DETECTED</div>
                <div style={{display:"flex",flexDirection:"column",gap:7}}>
                  {sel.layers.map((l,i)=>(
                    <div key={i} style={{display:"grid",gridTemplateColumns:"140px 1fr 44px",gap:10,alignItems:"center",padding:"7px 11px",background:"var(--elevated)",borderRadius:3,borderLeft:`3px solid ${l.c}`}}>
                      <div style={{fontSize:9,fontFamily:"var(--mono)",color:l.c}}>{l.l}</div>
                      <div style={{fontSize:11,color:"var(--t2)",lineHeight:1.3}}>{l.t}</div>
                      <div style={{fontFamily:"var(--mono)",fontSize:14,fontWeight:700,color:l.s>=80?"var(--red)":"var(--gold)",textAlign:"right"}}>{l.s}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </Panel>
          <Panel title="Synthesis Agent — Tactical Brief" actions={<div style={{display:"flex",gap:6}}><AiBadge/><OBtn small onClick={gen} disabled={loading}>{loading?"…":"Generate Brief"}</OBtn></div>}>
            <div style={{padding:"12px 14px"}}>
              {loading?<Spinner/>:brief?<div style={{fontSize:13,lineHeight:1.75,color:"var(--t2)",borderLeft:"2px solid var(--gold)",paddingLeft:14}}>{brief}</div>:<div style={{fontSize:11,color:"var(--t3)",fontStyle:"italic"}}>The Synthesis Agent reasons across all converged signals and generates a single tactical action brief — who should call, what to say, what to offer in the first 5 minutes.</div>}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
};

/* ─── M&A DARK SIGNALS ──────────────────────────────────────────────────────── */
const MADark = ()=>{
  const [sel,setSel]=useState(D.maDark[0]);
  const [pitch,setPitch]=useState("");const[loading,setLoading]=useState(false);
  const cc=c=>c>=85?"var(--red)":c>=70?"#e07c30":"var(--gold)";
  async function gen(){
    setLoading(true);setPitch("");
    try{
      const r={json:async()=>({content:[{text:await import('./api/client.js').then(m=>m.ai.maStrategy({company:sel.company,deal_type:sel.type,value:sel.value,days:sel.days,confidence:sel.confidence,warmth:sel.warmth,signals:sel.signals})).then(d=>d.strategy).catch(e=>e.message)}]})}; const _ignore7=();
      const d=await r.json();setPitch(d.content?.[0]?.text||"Error.");
    }catch{setPitch("API error.");}
    setLoading(false);
  }
  return(
    <div style={{height:"100%",overflowY:"auto",padding:"20px 24px"}}>
      <PageHeader tag="M&A Intelligence" title="M&A Dark Signal Detector" sub="Cross-references options anomalies, executive LinkedIn spikes, corporate jet tracking (public ADS-B), and supply chain filings to detect deal formation 14–90 days before announcement."/>
      <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:10,marginBottom:16}}>
        <Metric label="Deal Signals Active" val={D.maDark.length} sub="in formation" accent="red"/>
        <Metric label="Avg Confidence" val={`${Math.round(D.maDark.reduce((s,d)=>s+d.confidence,0)/D.maDark.length)}%`} sub="signal accuracy" accent="gold"/>
        <Metric label="Est. Total Deal Value" val="$5.4B" sub="across active signals" accent="blue"/>
        <Metric label="Avg Days to Announce" val="32" sub="historical avg" accent="green"/>
      </div>
      <div style={{display:"grid",gridTemplateColumns:"260px 1fr",gap:12}}>
        <Panel>
          {D.maDark.map((d,i)=>(
            <div key={i} onClick={()=>{setSel(d);setPitch("");}} style={{padding:"12px 14px",borderBottom:"1px solid var(--border)",cursor:"pointer",background:sel.company===d.company?"var(--elevated)":"transparent",borderLeft:sel.company===d.company?"2px solid var(--gold)":"2px solid transparent"}}>
              <div style={{display:"flex",justifyContent:"space-between",marginBottom:5}}>
                <div style={{fontSize:12,fontWeight:500,color:"var(--t1)"}}>{d.company}</div>
                <div style={{fontFamily:"var(--mono)",fontSize:18,fontWeight:700,color:cc(d.confidence),lineHeight:1}}>{d.confidence}%</div>
              </div>
              <div style={{fontSize:10,color:"var(--t3)",marginBottom:5}}>{d.type}</div>
              <div style={{display:"flex",gap:5}}><T ch={d.value} color="gold"/><T ch={`${d.days}d`}/></div>
            </div>
          ))}
        </Panel>
        <div style={{display:"flex",flexDirection:"column",gap:12}}>
          <Panel>
            <div style={{padding:"16px 18px"}}>
              <div style={{display:"flex",justifyContent:"space-between",alignItems:"flex-start",marginBottom:12}}>
                <div>
                  <div style={{fontFamily:"var(--serif)",fontWeight:700,fontSize:20,letterSpacing:"-.02em",color:"var(--t1)",marginBottom:6}}>{sel.company}</div>
                  <div style={{display:"flex",gap:6,flexWrap:"wrap"}}>
                    <T ch={sel.type} color="red"/>
                    <T ch={sel.value} color="gold"/>
                    <T ch={`${sel.days} days est.`} color="blue"/>
                  </div>
                </div>
                <div style={{textAlign:"right"}}>
                  <div style={{fontFamily:"var(--mono)",fontSize:44,fontWeight:700,color:cc(sel.confidence),lineHeight:1}}>{sel.confidence}%</div>
                  <div style={{fontSize:8,color:"var(--t3)",fontFamily:"var(--mono)"}}>CONFIDENCE</div>
                </div>
              </div>
              <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:10,paddingTop:12,borderTop:"1px solid var(--border)"}}>
                <div>
                  <div style={{fontSize:9,color:"var(--t3)",fontFamily:"var(--mono)",marginBottom:8}}>DARK SIGNALS</div>
                  {sel.signals.map((s,i)=>(
                    <div key={i} style={{display:"flex",gap:7,marginBottom:7}}><span style={{color:"var(--gold)",fontSize:9,marginTop:3,flexShrink:0}}>◎</span><span style={{fontSize:11,color:"var(--t2)",lineHeight:1.4}}>{s}</span></div>
                  ))}
                </div>
                <div>
                  <div style={{fontSize:9,color:"var(--t3)",fontFamily:"var(--mono)",marginBottom:8}}>RELATIONSHIP WARMTH</div>
                  <SBar s={sel.warmth} color={sel.warmth>=50?"green":"blue"}/>
                  <div style={{marginTop:10,background:"var(--elevated)",border:"1px solid var(--border)",borderRadius:3,padding:"9px 11px"}}>
                    <div style={{fontSize:11,color:"var(--t2)"}}>{sel.warmth<30?"Cold approach required — identify 2nd-degree connections first.":sel.warmth<60?"Lukewarm path available. Move quickly — window is "+sel.days+" days.":"Warm relationship exists. Call today."}</div>
                  </div>
                </div>
              </div>
            </div>
          </Panel>
          <Panel title="AI Deal Pitch Strategy" actions={<div style={{display:"flex",gap:6}}><AiBadge/><OBtn small onClick={gen} disabled={loading}>{loading?"…":"Generate"}</OBtn></div>}>
            <div style={{padding:"12px 14px"}}>
              {loading?<Spinner/>:pitch?<div style={{fontSize:13,lineHeight:1.75,color:"var(--t2)",borderLeft:"2px solid var(--gold)",paddingLeft:14}}>{pitch}</div>:<div style={{fontSize:11,color:"var(--t3)",fontStyle:"italic"}}>Generate strategy: which deal seats to pitch, the opening line that demonstrates intelligence, and first-call agenda.</div>}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
};

/* ─── PITCH AUTOPSY ─────────────────────────────────────────────────────────── */
const PitchAutopsy = ()=>{
  const [tab,setTab]=useState("stats");
  const [debrief,setDebrief]=useState("");const[dbResult,setDbResult]=useState("");const[dbLoading,setDbLoading]=useState(false);
  const [campTarget,setCampTarget]=useState(D.clients[0]);const[camp,setCamp]=useState("");const[campLoading,setCampLoading]=useState(false);
  const wf=[
    {f:"Practice group head presented first",w:78,l:44},
    {f:"Case studies included in deck",w:71,l:31},
    {f:"Fixed-fee option offered",w:68,l:38},
    {f:"GC attended (not just legal ops)",w:82,l:52},
    {f:"Follow-up within 48 hours",w:74,l:29},
  ];
  async function analyze(){
    if(!debrief.trim())return;
    setDbLoading(true);setDbResult("");
    try{
      const r={json:async()=>({content:[{text:await import('./api/client.js').then(m=>m.ai.pitchDebrief({debrief_text:debrief})).then(d=>d.analysis).catch(e=>e.message)}]})}; const _ignore8=();
      const d=await r.json();setDbResult(d.content?.[0]?.text||"Error.");
    }catch{setDbResult("API error.");}
    setDbLoading(false);
  }
  async function genCamp(){
    setCampLoading(true);setCamp("");
    try{
      const r={json:async()=>({content:[{text:await import('./api/client.js').then(m=>m.ai.bdCampaign({client_id:campTarget.id})).then(d=>d.campaign).catch(e=>e.message)}]})}; const _ignore9=();
      const d=await r.json();setCamp(d.content?.[0]?.text||"Error.");
    }catch{setCamp("API error.");}
    setCampLoading(false);
  }
  return(
    <div style={{height:"100%",overflowY:"auto",padding:"20px 24px"}}>
      <PageHeader tag="BD Analytics" title="Pitch Autopsy & BD Campaigns" sub="Statistical win/loss analysis. AI debrief agent removes social friction from loss analysis. Multi-channel campaign orchestration for priority clients."/>
      <div style={{display:"flex",gap:8,marginBottom:16}}>
        {[{k:"stats",l:"Win/Loss Analysis"},{k:"debrief",l:"Loss Debrief Agent"},{k:"campaign",l:"Campaign Engine"}].map(t=>(
          <button key={t.k} onClick={()=>setTab(t.k)} style={{padding:"6px 14px",borderRadius:2,fontFamily:"var(--mono)",fontSize:10,letterSpacing:".06em",textTransform:"uppercase",border:`1px solid ${tab===t.k?"rgba(212,168,67,.35)":"transparent"}`,background:tab===t.k?"rgba(212,168,67,.08)":"transparent",color:tab===t.k?"var(--gold)":"var(--t2)",cursor:"pointer"}}>
            {t.l}
          </button>
        ))}
      </div>
      {tab==="stats"&&(
        <div>
          <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:10,marginBottom:14}}>
            <Metric label="YTD Win Rate" val="63.6%" change={18} dir="up" sub="vs prior quarter" accent="green"/>
            <Metric label="Total Pitches" val="35" sub="across practice groups" accent="blue"/>
            <Metric label="Best Quarter" val="Q1 2025" sub="72.7% win rate" accent="gold"/>
            <Metric label="Avg Deal Won" val="$420K" sub="first year revenue" accent="purple"/>
          </div>
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12,marginBottom:12}}>
            <Panel title="Win Rate by Quarter">
              <div style={{padding:"12px 14px"}}>
                <ResponsiveContainer width="100%" height={150}>
                  <BarChart data={D.pitches}>
                    <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false}/>
                    <XAxis dataKey="q" tick={{fill:"var(--t3)",fontSize:9,fontFamily:"'DM Mono'"}} axisLine={false} tickLine={false}/>
                    <YAxis tick={{fill:"var(--t3)",fontSize:9,fontFamily:"'DM Mono'"}} axisLine={false} tickLine={false}/>
                    <Tooltip content={<CTip/>}/>
                    <Bar dataKey="won" name="Won" fill="var(--green)" radius={[2,2,0,0]}/>
                    <Bar dataKey="lost" name="Lost" fill="rgba(224,82,82,.5)" radius={[2,2,0,0]}/>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Panel>
            <Panel title="Statistical Win Factors">
              <div style={{padding:"12px 14px",display:"flex",flexDirection:"column",gap:10}}>
                {wf.map(f=>(
                  <div key={f.f} style={{display:"grid",gridTemplateColumns:"1fr 80px 80px",gap:8,alignItems:"center"}}>
                    <div style={{fontSize:11,color:"var(--t2)"}}>{f.f}</div>
                    <div>
                      <div style={{fontSize:8,color:"var(--green)",fontFamily:"var(--mono)",marginBottom:2}}>WITH: {f.w}%</div>
                      <div style={{height:4,background:"var(--border)",borderRadius:2,overflow:"hidden"}}><div style={{width:`${f.w}%`,height:"100%",background:"var(--green)",borderRadius:2}}/></div>
                    </div>
                    <div>
                      <div style={{fontSize:8,color:"var(--red)",fontFamily:"var(--mono)",marginBottom:2}}>WITHOUT: {f.l}%</div>
                      <div style={{height:4,background:"var(--border)",borderRadius:2,overflow:"hidden"}}><div style={{width:`${f.l}%`,height:"100%",background:"rgba(224,82,82,.5)",borderRadius:2}}/></div>
                    </div>
                  </div>
                ))}
              </div>
            </Panel>
          </div>
        </div>
      )}
      {tab==="debrief"&&(
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:12}}>
          <Panel title="GC Debrief Agent" actions={<AiBadge/>}>
            <div style={{padding:"14px 16px"}}>
              <div style={{fontSize:12,color:"var(--t3)",lineHeight:1.7,marginBottom:12}}>Paste any post-pitch information — feedback received, what you observed, who won and why. ORACLE extracts root cause and builds improvement recommendations without the social awkwardness of asking directly.</div>
              <textarea style={{width:"100%",background:"var(--ink)",border:"1px solid var(--border2)",color:"var(--t1)",padding:"9px 10px",borderRadius:3,fontSize:12,outline:"none",resize:"none",lineHeight:1.6,marginBottom:10}} rows={8} placeholder="Paste post-pitch notes, informal feedback, observations about what went wrong, who the client chose and any context you have..." value={debrief} onChange={e=>setDebrief(e.target.value)}/>
              <OBtn onClick={analyze} disabled={dbLoading||!debrief.trim()} style={{width:"100%"}}>
                {dbLoading?"Analyzing…":"Analyze Loss"}
              </OBtn>
            </div>
          </Panel>
          <Panel title="Analysis Results">
            <div style={{padding:"14px 16px"}}>
              {dbLoading?<Spinner/>:dbResult?<div style={{fontSize:13,lineHeight:1.75,color:"var(--t2)",borderLeft:"2px solid var(--red)",paddingLeft:14}}>{dbResult}</div>:<div style={{fontSize:11,color:"var(--t3)",fontStyle:"italic"}}>Root cause, what the winning firm did differently, and whether to re-pitch or walk away — will appear here.</div>}
            </div>
          </Panel>
        </div>
      )}
      {tab==="campaign"&&(
        <div style={{display:"grid",gridTemplateColumns:"240px 1fr",gap:12}}>
          <Panel>
            <div style={{padding:"10px 12px",borderBottom:"1px solid var(--border)",fontFamily:"var(--mono)",fontSize:9,color:"var(--t3)",letterSpacing:".1em"}}>SELECT TARGET CLIENT</div>
            {D.clients.map(c=>(
              <div key={c.id} onClick={()=>{setCampTarget(c);setCamp("");}} style={{padding:"10px 12px",borderBottom:"1px solid var(--border)",cursor:"pointer",background:campTarget?.id===c.id?"var(--elevated)":"transparent",borderLeft:campTarget?.id===c.id?"2px solid var(--gold)":"2px solid transparent"}}>
                <div style={{fontSize:11,fontWeight:500,color:"var(--t1)",marginBottom:2}}>{c.name}</div>
                <div style={{fontSize:9,color:"var(--t3)"}}>{c.industry} · {c.partner}</div>
              </div>
            ))}
          </Panel>
          <Panel title="AI Campaign Orchestrator" actions={<div style={{display:"flex",gap:6}}><AiBadge/><OBtn small onClick={genCamp} disabled={campLoading}>{campLoading?"…":"▷ Generate Campaign"}</OBtn></div>}>
            <div style={{padding:"14px 16px"}}>
              <div style={{fontFamily:"var(--serif)",fontWeight:700,fontSize:16,color:"var(--t1)",marginBottom:12}}>{campTarget?.name}</div>
              {campLoading?<Spinner/>:camp?<div style={{background:"var(--ink)",border:"1px solid var(--border)",borderRadius:3,padding:"13px 15px"}}><pre style={{fontFamily:"var(--sans)",fontSize:12,lineHeight:1.8,color:"var(--t2)",whiteSpace:"pre-wrap",margin:0}}>{camp}</pre></div>:<div style={{fontSize:12,color:"var(--t3)",lineHeight:1.7}}>Generate a 4-step 6-week coordinated BD campaign. ORACLE considers the client's industry, flight risk, wallet share gap, and practice group mix to design the optimal touchpoint sequence.</div>}
            </div>
          </Panel>
        </div>
      )}
    </div>
  );
};

/* ─── HEAT MAP ──────────────────────────────────────────────────────────────── */
const HeatMap = ()=>{
  const partners=["S. Chen","M. Webb","D. Park","J. Okafor","P. Rodrigues"];
  const ownership={1:["S. Chen","S. Chen"],2:["M. Webb"],3:["D. Park"],4:["J. Okafor"],5:["S. Chen"],6:["P. Rodrigues"],7:["M. Webb"],8:["D. Park"]};
  const [hover,setHover]=useState(null);
  const score=(pid,cid)=>{
    const owns=(ownership[cid]||[]).includes(pid);
    if(owns)return 60+Math.floor(Math.random()*40);
    return Math.random()>.55?Math.floor(Math.random()*40)+5:0;
  };
  const matrix=partners.map(p=>({p,cells:D.clients.map(c=>({c,s:score(p,c.id),owns:(ownership[c.id]||[]).includes(p)}))}));
  const cc=s=>s===0?"transparent":s>=70?"rgba(61,186,122,"+(0.1+s/200)+")":s>=40?"rgba(212,168,67,"+(0.08+s/300)+")":"rgba(74,143,255,"+(0.06+s/500)+")";
  return(
    <div style={{height:"100%",overflowY:"auto",padding:"20px 24px"}}>
      <PageHeader tag="Relationship Intelligence" title="Relationship Heat Map" sub="Every partner–client relationship scored by recency, depth, and cross-practice penetration. Green = primary. Gold = active. Blue = aware. Blank = whitespace."/>
      <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:10,marginBottom:16}}>
        <Metric label="Total Relationships" val={matrix.reduce((s,r)=>s+r.cells.filter(c=>c.s>0).length,0)} sub="partner-client pairs" accent="blue"/>
        <Metric label="Primary (Owned)" val={matrix.reduce((s,r)=>s+r.cells.filter(c=>c.owns).length,0)} sub="direct ownership" accent="green"/>
        <Metric label="Whitespace Pairs" val={matrix.reduce((s,r)=>s+r.cells.filter(c=>c.s===0).length,0)} sub="zero relationship" accent="red"/>
        <Metric label="Cross-sell Opps" val={D.clients.filter(c=>c.pgs.length<3).length} sub="single-practice clients" accent="gold"/>
      </div>
      <div style={{display:"grid",gridTemplateColumns:"1fr 260px",gap:12}}>
        <Panel title="Partner × Client Matrix">
          <div style={{padding:"14px 16px",overflowX:"auto"}}>
            <div style={{display:"flex",gap:12,marginBottom:12}}>
              {[{c:"rgba(61,186,122,.4)",l:"Primary 75–100"},{c:"rgba(212,168,67,.3)",l:"Active 40–74"},{c:"rgba(74,143,255,.2)",l:"Aware 1–39"},{c:"transparent",l:"No Relationship"}].map(i=>(
                <div key={i.l} style={{display:"flex",gap:5,alignItems:"center"}}>
                  <div style={{width:10,height:10,background:i.c,border:"1px solid var(--border)",borderRadius:2}}/>
                  <span style={{fontSize:9,color:"var(--t3)",fontFamily:"var(--mono)"}}>{i.l}</span>
                </div>
              ))}
            </div>
            <table style={{borderCollapse:"separate",borderSpacing:3}}>
              <thead>
                <tr>
                  <th style={{width:100,padding:"3px 6px",textAlign:"left",fontSize:9,color:"var(--t3)",fontFamily:"var(--mono)",fontWeight:"normal"}}>↓ Partner / Client →</th>
                  {D.clients.map(c=><th key={c.id} style={{padding:"3px 4px",fontSize:8,color:"var(--t3)",fontFamily:"var(--mono)",fontWeight:"normal",width:72,textAlign:"center",overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{c.name.split(" ")[0]}</th>)}
                </tr>
              </thead>
              <tbody>
                {matrix.map(row=>(
                  <tr key={row.p}>
                    <td style={{padding:"3px 6px",fontSize:11,fontWeight:500,whiteSpace:"nowrap",color:"var(--t2)"}}>{row.p}</td>
                    {row.cells.map(cell=>(
                      <td key={cell.c.id} onMouseEnter={()=>setHover({p:row.p,c:cell.c,s:cell.s,owns:cell.owns})} onMouseLeave={()=>setHover(null)} style={{padding:3,cursor:"pointer"}}>
                        <div style={{width:72,height:32,background:cc(cell.s),border:`1px solid ${cell.owns?"rgba(61,186,122,.35)":"var(--border)"}`,borderRadius:3,display:"flex",alignItems:"center",justifyContent:"center",fontSize:10,fontFamily:"var(--mono)",color:cell.s===0?"var(--t4)":cell.s>=70?"var(--green)":cell.s>=40?"var(--gold)":"#7fb3ff",transition:"all .1s",fontWeight:cell.owns?600:400}}>
                          {cell.s===0?"—":cell.s}{cell.owns&&<span style={{fontSize:6,marginLeft:1}}>●</span>}
                        </div>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
        <div style={{display:"flex",flexDirection:"column",gap:10}}>
          <Panel title="Cell Inspector" style={{minHeight:120}}>
            <div style={{padding:"12px 14px"}}>
              {hover?<div>
                <div style={{fontWeight:600,fontSize:13,color:"var(--t1)",marginBottom:2}}>{hover.c.name}</div>
                <div style={{fontSize:10,color:"var(--t3)",marginBottom:10}}>{hover.p}</div>
                {[["Score",hover.s||"—"],["Ownership",hover.owns?"Primary":"Secondary"],["Revenue",fmt(hover.c.rev)]].map(([l,v])=>(
                  <div key={l} style={{display:"flex",justifyContent:"space-between",marginBottom:5}}>
                    <span style={{fontSize:10,color:"var(--t3)",fontFamily:"var(--mono)"}}>{l}</span>
                    <span style={{fontSize:11,color:"var(--t1)",fontFamily:"var(--mono)"}}>{v}</span>
                  </div>
                ))}
              </div>:<div style={{fontSize:10,color:"var(--t3)"}}>Hover over a cell to inspect the relationship.</div>}
            </div>
          </Panel>
          <Panel title="Top Whitespace Opportunities" style={{flex:1}}>
            <div style={{padding:"10px 12px"}}>
              {matrix.flatMap(row=>row.cells.filter(c=>c.s===0).map(c=>({p:row.p,c:c.c}))).slice(0,6).map((w,i)=>(
                <div key={i} style={{padding:"7px 9px",background:"var(--elevated)",border:"1px solid var(--border)",borderRadius:3,marginBottom:7}}>
                  <div style={{fontSize:11,fontWeight:500,color:"var(--t1)"}}>{w.c.name.split(" ").slice(0,2).join(" ")}</div>
                  <div style={{fontSize:9,color:"var(--t3)"}}>{w.p} has zero relationship</div>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
};


/* ─── Live Signal Ticker ─────────────────────────────────────────────────────── */
const TickerBar = () => {
  const items = [
    "CRITICAL · Aurelia Capital — Davies Ward pitch detected (14 devices, 2.5h)",
    "HIGH · Arctis Mining — SEDAR confidentiality agreement filed Nov 14",
    "HIGH · Westbrook Digital — BreachForums credential leak 03:14 AM",
    "SIGNAL · Arctis Mining CEO jet: Bay Street 3× in 10 days — M&A forming",
    "REGULATORY · OSFI Guideline B-20 Amendment — Ember Financial affected",
    "MEDIUM · Centurion Pharma — Osler office visit 8 devices 3.1h avg",
    "HIGH · Caldwell Steel — satellite: parking lot 94% → 31% over 4 weeks",
  ];
  const text = items.join("   ·   ") + "   ·   " + items.join("   ·   ");
  return (
    <div style={{height:26,background:"var(--panel)",borderBottom:"1px solid var(--border)",overflow:"hidden",display:"flex",alignItems:"center",flexShrink:0}}>
      <div style={{flexShrink:0,padding:"0 12px",fontFamily:"var(--mono)",fontSize:8,fontWeight:500,letterSpacing:".14em",color:"var(--gold)",textTransform:"uppercase",borderRight:"1px solid var(--border)",height:"100%",display:"flex",alignItems:"center"}}>Live</div>
      <div style={{overflow:"hidden",flex:1}}>
        <div style={{display:"inline-block",whiteSpace:"nowrap",animation:"ticker 80s linear infinite",fontFamily:"var(--mono)",fontSize:9,color:"var(--t2)",letterSpacing:".04em"}}>{text}</div>
      </div>
    </div>
  );
};

/* ─── ROUTER ─────────────────────────────────────────────────────────────────── */
const PAGES = {
  cmd: CommandCenter, churn: ChurnPredictor, reg: RegulatoryRipple, heat: HeatMap,
  triggers: LiveTriggers,
  geomap: GeoMap, jets: JetTracker, foot: FootTraffic, sat: Satellite, permits: PermitRadar,
  precrime: PreCrime, mandates: MandateFormation, ma: MADark,
  comp: CompIntel, wallet: WalletShare, alumni: AlumniActivator, gc: GCProfiler,
  assoc: ()=><div style={{padding:"40px 28px",color:"var(--t2)"}}><PageHeader tag="Associate Development" title="Associate Accelerator" sub="Personal BD dashboards, warm path mapper, content studio, and shadow origination tracker for all firm associates."/><div style={{padding:20,background:"var(--card)",border:"1px solid var(--border)",borderRadius:3,fontSize:13,color:"var(--t3)",lineHeight:1.75,fontFamily:"var(--sans)"}}>Full module available in production build. Includes: personal BD dashboard per associate, AI LinkedIn post generator, warm path mapper, and shadow origination tracker for partnership review.</div></div>,
  pitch: PitchAutopsy,
  coaching: BDCoaching,
  ghost: GhostStudio,
};

/* ─── APP ────────────────────────────────────────────────────────────────────── */
export default function App() {
  const [page, setPage] = useState("cmd");
  const Page = PAGES[page] || CommandCenter;
  return (
    <>
      <FontLoader />
      <style>{`
        @keyframes glow{0%,100%{box-shadow:0 0 8px rgba(212,168,67,.2)}50%{box-shadow:0 0 22px rgba(212,168,67,.5)}}
      `}</style>
      <div style={{display:"flex",height:"100vh",overflow:"hidden",background:"var(--ink)",fontFamily:"var(--sans)",position:"relative"}}>
        {/* Grid bg */}
        <div style={{position:"fixed",inset:0,backgroundImage:"linear-gradient(rgba(22,32,54,.4) 1px,transparent 1px),linear-gradient(90deg,rgba(22,32,54,.4) 1px,transparent 1px)",backgroundSize:"32px 32px",pointerEvents:"none",zIndex:0}}/>
        {/* Scan line */}
        <div className="scan" style={{position:"fixed",left:0,right:0,height:120,background:"linear-gradient(transparent,rgba(212,168,67,.015),transparent)",pointerEvents:"none",zIndex:1,animation:"scan 8s linear infinite"}}/>
        <div style={{position:"relative",zIndex:10,flexShrink:0}}>
          <Sidebar active={page} set={setPage}/>
        </div>
        <div style={{flex:1,overflow:"hidden",position:"relative",zIndex:1,display:"flex",flexDirection:"column"}}>
          <div style={{height:2,background:"linear-gradient(90deg,var(--gold),transparent 55%)",flexShrink:0}}/>
          <div key={page} style={{flex:1,overflow:"hidden"}} className="fadeup">
            <Page setPage={setPage}/>
          </div>
        </div>
      </div>
    </>
  );
}
