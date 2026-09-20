from __future__ import annotations

from fastapi.responses import HTMLResponse

DASHBOARD = """<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>Aegis Forge | Incident Control</title>
<style>
:root{color-scheme:dark;--ink:#e7f1f5;--muted:#91aab5;--line:#244351;--panel:#102831;--accent:#5ee0bf;--warn:#ffc56d;--bg:#061217}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 80% 0,#123541 0,#061217 42%);color:var(--ink);font:15px/1.5 ui-sans-serif,system-ui,sans-serif}main{max-width:1180px;margin:auto;padding:42px 24px}.eyebrow{color:var(--accent);letter-spacing:.14em;text-transform:uppercase;font-size:12px}h1{font-size:clamp(34px,6vw,68px);line-height:1;margin:14px 0 10px;max-width:780px}p{color:var(--muted)}.grid{display:grid;grid-template-columns:1.2fr .8fr;gap:18px;margin-top:34px}.panel{background:rgba(16,40,49,.84);border:1px solid var(--line);border-radius:12px;padding:20px;box-shadow:0 18px 70px #0004}.panel h2{font-size:16px;margin:0 0 15px}.status{display:flex;gap:10px;align-items:center;color:var(--accent)}.dot{width:9px;height:9px;background:var(--accent);border-radius:50%;box-shadow:0 0 18px var(--accent)}textarea{width:100%;min-height:150px;resize:vertical;background:#071920;border:1px solid var(--line);border-radius:8px;color:var(--ink);padding:14px;font:inherit}button{margin-top:12px;background:var(--accent);border:0;border-radius:7px;padding:11px 16px;color:#06211d;font-weight:700;cursor:pointer}button:disabled{opacity:.5}.result{white-space:pre-wrap;color:#dcecf0}.chips{display:flex;flex-wrap:wrap;gap:8px}.chip{border:1px solid var(--line);border-radius:99px;padding:5px 9px;color:var(--muted);font-size:12px}.metric{font-size:30px;color:var(--accent)}@media(max-width:780px){.grid{grid-template-columns:1fr}main{padding:28px 16px}}
</style></head><body><main><div class=\"eyebrow\">Local AI incident operations</div><h1>Investigate with evidence. Act with boundaries.</h1><p>Aegis Forge coordinates retrieval, read-only tools, local models, memory, and an auditable trace in one operator workflow.</p>
<div class=\"grid\"><section class=\"panel\"><h2>New investigation</h2><textarea id=\"incident\" placeholder=\"Describe the operational signal...\">Database connections are exhausted and retries are increasing in payments API</textarea><button id=\"run\" onclick=\"investigate()\">Run guarded investigation</button><div id=\"result\" class=\"result\" style=\"margin-top:18px\"></div></section><aside class=\"panel\"><h2>Control plane</h2><div class=\"status\"><span class=\"dot\"></span><span id=\"health\">Checking readiness...</span></div><p>Runtime telemetry</p><div id=\"metrics\" class=\"chips\"></div><p>Principles</p><div class=\"chips\"><span class=\"chip\">allowlisted tools</span><span class=\"chip\">prompt defense</span><span class=\"chip\">SQLite memory</span><span class=\"chip\">Ollama-ready</span></div></aside></div></main>
<script>async function load(){const h=await fetch('/ready');const data=await h.json();document.querySelector('#health').textContent=data.status+' · database '+data.database;const m=await fetch('/metrics/json');const x=await m.json();document.querySelector('#metrics').innerHTML='<span class=\"metric\">'+x.duration_count+'</span><span class=\"chip\">observed operations</span><span class=\"chip\">avg '+x.duration_avg_ms+'ms</span>'}async function investigate(){const b=document.querySelector('#run'),out=document.querySelector('#result');b.disabled=true;out.textContent='Running security gate, retrieval, tools, and synthesis...';try{const r=await fetch('/api/investigate',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({incident:document.querySelector('#incident').value,namespace:'dashboard'})});const x=await r.json();out.textContent=x.detail?JSON.stringify(x.detail,null,2):x.summary+'\n\nConfidence: '+x.confidence+'\nRecommendations:\n- '+x.recommendations.join('\n- ')+'\n\nTrace events: '+x.trace.length}catch(e){out.textContent='Request failed: '+e}finally{b.disabled=false;load()}}load()</script></body></html>"""


def dashboard() -> HTMLResponse:
        pipeline = """
        <section class="panel" style="margin-top:18px"><h2>Live investigation pipeline</h2>
        <div id="pipeline" class="chips"><span class="chip">security</span><span class="chip">RAG</span><span class="chip">routing</span><span class="chip">tools</span><span class="chip">decision</span><span class="chip">memory</span><span class="chip">approval</span></div>
        <pre id="events" class="result" style="max-height:180px;overflow:auto;margin-top:12px">Events will appear here after a run.</pre></section>
        <script>
        const nativeFetch=window.fetch;
        window.fetch=async function(...args){const response=await nativeFetch(...args);if(String(args[0]).includes('/api/investigate')){response.clone().json().then(data=>{window.lastRunId=data.run_id});}return response;};
        const originalInvestigate=investigate;
        investigate=async function(){
            await originalInvestigate();
            const text=document.querySelector('#result').textContent;
            const match=text.match(/Trace events: (\\d+)/);
            document.querySelector('#events').textContent=match?`Completed ${match[1]} traced stages. Open the run trace endpoint for the full event payload.`:text;
            if(window.lastRunId){const stream=new EventSource('/api/runs/'+window.lastRunId+'/events');stream.onmessage=event=>{document.querySelector('#events').textContent+=`\\n${event.type}: ${event.data}`;};}
        };
        </script>
        """
        return HTMLResponse(DASHBOARD.replace("</main>", pipeline + "</main>"))
