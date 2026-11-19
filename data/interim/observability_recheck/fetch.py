"""Download the candidate observability pages of each tool (raw text, curl) into snapshots/ and log them."""
import re,subprocess,csv,os,datetime,sys
sys.path.insert(0,'.')
inc=re.compile(r'cost|token|usage|dashboard|monitor|metric|analytic|data-?model|alert|session|trac|observ|span|latency|ttft|thread|report|insight|log',re.I)
exc=re.compile(r'integrat|cookbook|guides?/|/rest/|api-reference|/api/|sdk|self-host|blog|changelog|pricing|eval|scor|prompt|dataset|experiment|playground|deploy|admin|billing|security|sso|rbac|faq|tutorial|example|quickstart|get-started|getting-started|migrat|release|red-team|gateway|optimi|annotat|feedback|login|otel|opentelemetry|provider|registry|recipes|frameworks?/|libraries|launch|sweeps|artifacts|training|kubernetes|slurm|storage|network|tts|voice|simulat|scenario|mcp|skill|/cli|/ko/|/ja/|/fr/|videos|use-cases|typescript|python|java|golang|ruby|csharp|audit|governance|coding-agents|install|llms-full|troubleshoot|images|multimodal|offline|distributed|compare/|cost-intelligence|langy|limits|flushing|browser|rate-limit|moderation|caching|llm-security|exception|human|queue|label|export|share|privacy|mask|redact|sampling|environment|version|attachment|media|reference/|/kb/|/metrics/|luna|trace-with|trace-(anthropic|bedrock|deepseek|litellm|openai|claude|gemini|deep-agents)|_llms|trace-generator|trace-replicas|trace-without|upload-files|conditional|log-retriever|nest-traces|access-current|manage-trace|user-id|/tags|metadata|continuing|task-extraction|/name|customers|projects|dropping|users',re.I)
SRC={'langfuse':('index/langfuse.txt',None,''),'helicone':('index/helicone.txt',None,''),'laminar':('index/laminar.txt',None,''),'langwatch':('index/langwatch.txt',None,''),'opik':('index/opik.txt',None,''),
'weave':('index/weave_wb.txt','wandb/weave',''),'mlflow':('index/mlflow.txt','genai','https://mlflow.org'),'galileo':('index/galileo_docs.txt',None,''),'phoenix':('index/phoenix.txt',None,''),
'braintrust':('index/braintrust_guides.txt','NONE',''),'langsmith':('index/langsmith_monitor.txt',None,''),'confidentai':('index/confidentai.txt',None,''),'promptfoo':('index/promptfoo.txt',None,'https://www.promptfoo.dev')}
EXTRA={'weave':['https://docs.coreweave.com/products/wandb/weave/'+p+'.md' for p in 'guides/tracking/trace-agents guides/tracking/view-agent-activity guides/tracking/view-agent-signals guides/tracking/trace-agents-attributes guides/tracking/costs guides/tools/saved-views guides/tracking/trace-plots guides/tracking/tracing guides/tracking/trace-tree guides/tracking/querying-calls guides/tracking/threads guides/tracking/view-call guides/tracking/get-call-object guides/tracking/ops guides/tools/comparison concepts/what-is-weave'.split()],
'braintrust':['https://docs.braintrust.dev/'+p+'.md' for p in 'instrument/trace-llm-calls instrument/advanced-tracing instrument/trace-application-logic observe/index observe/view-logs observe/filter observe/examine-traces observe/dashboards/index observe/dashboards/create observe/dashboards/build-charts observe/alerts deploy/monitor'.split()],
'galileo':['https://docs.galileo.ai/'+p+'.md' for p in 'concepts/logging/overview how-to-guides/basics/set-up-alerts-on-logs concepts/costs/model-pricing-settings how-to-guides/basics/manual-span-creation/manual-span-creation'.split()],
'langwatch':['https://langwatch.ai/docs/'+p+'.md' for p in 'integration/python/tutorials/tracking-llm-costs integration/python/tutorials/tracking-time-to-first-token concepts integration/overview features/triggers features/alerts ai-gateway/observability'.split()],
'langfuse':['https://langfuse.com/docs/observability/data-model.md','https://langfuse.com/docs/observability/features/token-and-cost-tracking.md','https://langfuse.com/docs/metrics/overview.md','https://langfuse.com/docs/metrics/features/custom-dashboards.md','https://langfuse.com/docs/metrics/features/metrics-api.md','https://langfuse.com/docs/observability/features/agent-graphs.md','https://langfuse.com/docs/observability/features/observation-types.md','https://langfuse.com/docs/observability/features/sessions.md','https://langfuse.com/docs/observability/features/log-levels.md','https://langfuse.com/docs/observability/overview.md'],
'promptfoo':['https://www.promptfoo.dev/docs/tracing/','https://www.promptfoo.dev/docs/configuration/expected-outputs/deterministic/','https://www.promptfoo.dev/docs/configuration/reference/','https://www.promptfoo.dev/docs/usage/web-ui/','https://www.promptfoo.dev/docs/configuration/outputs/']}
def urls(t):
    f,must,host=SRC[t]; out=[]
    for u in re.findall(r'\((https?://[^)\s]+|/[^)\s]+)\)',open(f).read()):
        if must and must not in u: continue
        if inc.search(u) and not exc.search(u):
            u=host+u if u.startswith('/') else u
            if u not in out: out.append(u)
    if t=='langfuse': out=[]
    for u in EXTRA.get(t,[]):
        if u not in out: out.append(u)
    return out
if __name__=='__main__':
    os.makedirs('snapshots',exist_ok=True); today=datetime.date.today().isoformat()
    only=sys.argv[1:]
    rows=[]
    for t in SRC:
        if only and t not in only: continue
        us=urls(t)
        for u in us:
            slug=re.sub(r'[^a-z0-9]+','-',re.sub(r'^https?://[^/]+/(docs/)?','',u).lower().replace('.md','')).strip('-')[-70:]
            fn='%s__%s.txt'%(t,slug or 'index')
            r=subprocess.run(['curl','-sL','-m','40','-A','Mozilla/5.0','-o','snapshots/'+fn,'-w','%{http_code}',u],capture_output=True,text=True)
            n=os.path.getsize('snapshots/'+fn) if os.path.exists('snapshots/'+fn) else 0
            rows.append([t,u,fn,r.stdout,n,today])
        print(t,len(us))
    new=not os.path.exists('fetch_log.csv')
    with open('fetch_log.csv','a',newline='') as fh:
        w=csv.writer(fh)
        if new: w.writerow(['tool','url','snapshot_file','http_code','bytes','access_date'])
        w.writerows(rows)
