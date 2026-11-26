"""CLI:  python -m mother <명령>   (도움말: python -m mother -h)"""
import argparse
import json
import sys

from . import agents, business, llm, mother, providers, store, tools


def _ROUNDS():
    from .viability import _cfg
    return _cfg()["upgrade_rounds"]


def p(*a):
    print(*(store.redact(x) for x in a), flush=True)


def cmd_status(_=None):
    ideas = store.load_json("ideas.json", [])
    act = [i for i in ideas if i["status"] == "active"]
    lines = [f"오늘 비용 ${store.spend_on()} / ${store.cfg()['budget']['daily_usd']}",
             f"아이디어 {len(ideas)}개 · 진행중 {len(act)} · 탈락 {sum(i['status'] == 'killed' for i in ideas)}"]
    for i in act:
        m = business.metrics(i)
        lines.append(f"  {i['id']} {i['title']} [{i['market']}] 매출 ${m['revenue']} ROI {m['roi']:+.0%} {m['age']}일차")
    for n in agents.all_agents():
        avg, rows = agents.score(n)
        if avg is not None:
            lines.append(f"  에이전트 {n}: 평균 {avg:.1f}점 ({len(rows)}회)")
    return "\n".join(lines)


def cmd_jobs():
    """jarvis/jobs.json 작업 큐 처리 (JARVIS 브릿지 호환)."""
    q = store.ROOT / "jarvis" / "jobs.json"
    if not q.exists():
        return "작업 없음"
    done = set(store.load_json("jobs_done.json", []))
    out_dir = store.REPORTS / "jobs"
    out_dir.mkdir(exist_ok=True)
    msgs = []
    for job in json.loads(q.read_text(encoding="utf-8")):
        if job["id"] in done:
            continue
        task = job["task"].strip()
        if task == "status":
            res = cmd_status()
        elif task.startswith("scout"):
            res = json.dumps(business.scout(task.split()[1] if len(task.split()) > 1 else None), ensure_ascii=False, indent=1)
        else:
            res = mother.run(task)[0]["summary"]
        (out_dir / f"{job['id']}.md").write_text(f"# {job['id']}\n{task}\n\n{res}\n", encoding="utf-8")
        done.add(job["id"])
        msgs.append(f"{job['id']} 완료")
    store.save_json("jobs_done.json", sorted(done))
    return "\n".join(msgs) or "새 작업 없음"


def cmd_daily():
    """매일 자동: ROI 리뷰 → 신규 발굴(요일별 1개 시장) → 저성과 에이전트 업그레이드 → 작업큐."""
    log = [f"# 일일 리포트 {store.today()}"]
    try:
        from . import collector
        new_src = collector.discover()
        added, _ = collector.collect()
        log += [f"## 오늘의 트렌드 (새 소식 {added}건 · 출처 {len(collector.feeds())}곳"
                + (f" · 새 출처: {', '.join(new_src)}" if new_src else "") + ")",
                collector.search(category="trend", limit=8)]
        rows, plans = business.review()
        log += ["## 사업 리뷰"] + [f"- {it['id']} {it['title']}: **{act}** ROI {m['roi']:+.0%} {plans.get(it['id'], {}).get('plan', '')}"
                                  for it, m, act in rows] or ["- 진행중 사업 없음"]
        mk = store.cfg()["markets"][store.now().weekday() % len(store.cfg()["markets"])]["code"]
        new = business.scout(mk)
        log += [f"## 신규 발굴 ({mk})"] + [f"- {i['id']} {i['score']}점 [{i['status']}] {i['title']} — {i['first_step']}" for i in new]
        from . import pipelines, product, publish
        ap = store.cfg().get("autopilot", {})
        if ap.get("make_products"):  # 진행 중인데 상품이 없는 사업 → 자동 제작 (하루 1개)
            from . import viability
            todo = [i for i in store.load_json("ideas.json", []) if i["status"] == "active" and not i.get("product")]
            for i in todo[:2]:  # 테스트 안 한 사업은 먼저 생존 테스트
                if not i.get("viability"):
                    _, r = viability.test_idea(i["id"])
                    log += [f"- 🧪 {i['id']} {'생존' if r['pass'] else '탈락'}: {r['why']}"]
            todo = [i for i in store.load_json("ideas.json", []) if i["status"] == "active" and not i.get("product")
                    and (i.get("viability") or {}).get("pass")]
            if todo:
                r = product.make(todo[0]["id"])
                log += ["## 상품 자동 제작", f"- {todo[0]['id']} {r['title']} · {r['sections']}장 · {r['chars']:,}자" + (" · PDF" if r["pdf"] else "")]
        for name, fn in (("숏츠 자동 업로드", publish.shorts), ("블로그 자동 게시", publish.blog)):
            try:
                log += [f"## {name}", fn() or "- 없음"]
            except llm.BudgetExceeded:
                raise
            except Exception as e:
                log += [f"## {name}", f"- 실패: {type(e).__name__}: {str(e)[:150]}"]
        if store.now().weekday() == 0:  # 매주 월요일: 모든 사업·파이프라인 재검증 → 살아남은 것만 유지
            from . import viability
            log += ["## 🧪 주간 생존 토너먼트"] + [f"- {r}" for r in viability.test_all()]
        ran = pipelines.run_due()
        log += ["## 자동 파이프라인"] + ([f"- {r}" for r in ran] or ["- 오늘 실행할 것 없음"])
        ups = [agents.upgrade(n) for n in agents.all_agents()]
        log += ["## 에이전트 업그레이드"] + [f"- {u['name']} → v{u['version']}" for u in ups if u] or ["- 없음"]
        log += ["## 작업큐", cmd_jobs()]
    except llm.BudgetExceeded as e:
        log.append(f"⚠️ {e}")
    log += ["## 현황", "```", cmd_status(), "```"]
    rp = store.REPORTS / f"daily-{store.today()}.md"
    rp.write_text("\n".join(log) + "\n", encoding="utf-8")
    return f"저장: {rp.relative_to(store.ROOT)}\n" + "\n".join(log)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="mother", description="LINK 마더 에이전트")
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("run", help="목표를 회사처럼 처리").add_argument("goal")
    a = sp.add_parser("ask", help="특정 에이전트에게 직접 지시")
    a.add_argument("agent"); a.add_argument("task")

    ag = sp.add_parser("agent", help="에이전트 관리")
    ag.add_argument("action", choices=["list", "new", "upgrade", "add-skill"])
    ag.add_argument("name", nargs="?"); ag.add_argument("arg", nargs="?")
    ag.add_argument("--force", action="store_true")

    s = sp.add_parser("search", help="LLM 없이 바로 검색 (토큰 0)")
    s.add_argument("kind", choices=["google", "github", "skills", "prompts", "agents", "code", "youtube", "trending"])
    s.add_argument("query", nargs="?", default="")
    s.add_argument("--region", default="KR"); s.add_argument("--lang", default="ko")
    sp.add_parser("crawl", help="페이지 크롤링 (토큰 0)").add_argument("url")
    sk = sp.add_parser("skill", help="깃허브 스킬/프롬프트 가져오기")
    sk.add_argument("repo"); sk.add_argument("path"); sk.add_argument("--agent")

    b = sp.add_parser("biz", help="사업 발굴·수익 관리")
    b.add_argument("action", choices=["scout", "list", "approve", "log", "review"])
    b.add_argument("id", nargs="?")
    b.add_argument("--market"); b.add_argument("--revenue", type=float, default=0)
    b.add_argument("--cost", type=float, default=0); b.add_argument("--currency", default="USD")
    b.add_argument("--note", default="")

    ai = sp.add_parser("ai", help="모든 AI 통합: 연결현황·직접질문·아레나(모델 대결)")
    ai.add_argument("action", choices=["status", "ask", "arena", "check"])
    ai.add_argument("prompt", nargs="?", default="")
    ai.add_argument("--model", default="auto", help="auto 또는 provider:model (예: gemini:gemini-flash-latest)")

    nw = sp.add_parser("news", help="트렌드·뉴스 수집 / news add <사이트> / news sources / news discover")
    nw.add_argument("query", nargs="?", default=""); nw.add_argument("url", nargs="?", default="")
    hk = sp.add_parser("hook", help="숏츠 훅·제목 채점 (토큰 0)")
    hk.add_argument("text"); hk.add_argument("--title", default=""); hk.add_argument("--thumb", default="")

    pl = sp.add_parser("pipeline", help="자동화 파이프라인: new \"하고 싶은 일\" / list / run <이름> / off <이름>")
    pl.add_argument("action", choices=["new", "list", "run", "off", "on"]); pl.add_argument("arg", nargs="?", default="")
    tt = sp.add_parser("test", help="생존 테스트: 인터넷 조사→AI 경쟁 추정→수익 시뮬레이션 (test I0001 / test all / test pipeline 이름)")
    tt.add_argument("target"); tt.add_argument("name", nargs="?", default="")
    sh_ = sp.add_parser("shorts", help="숏츠 대본→영상→유튜브 자동 업로드 (--private: 비공개 시험 업로드)")
    sh_.add_argument("--private", action="store_true"); sh_.add_argument("--topic", default="", help="이 주제로 만들기")
    sh_.add_argument("--skip", default="", help="대기 대본 빼기 (예: 007,008)")
    st = sp.add_parser("story", help="AI 실사 스토리: story new \"로그라인\" [--genre 판타지] / story next <slug> / story plan <slug>(Gemini 장면용 대본) / story render <slug> / story list")
    st.add_argument("action", choices=["new", "next", "list", "plan", "render"]); st.add_argument("arg", nargs="?", default="")
    st.add_argument("--genre", default=""); st.add_argument("--private", action="store_true")
    od = sp.add_parser("order", help="크몽·숨고 주문 처리: order <blog|review|detail|translate|ppt> \"고객 요청\"")
    od.add_argument("service"); od.add_argument("request")
    sp.add_parser("blog", help="블로그 글 작성→Blogger 자동 게시")
    sp.add_parser("benchmark", help="유튜브 인기 AI 숏츠 수집(대본 참고용)")
    mk = sp.add_parser("make", help="사업 아이디어 → 판매용 상품(원고·PDF·판매페이지) 자동 제작")
    mk.add_argument("id"); mk.add_argument("--pages", type=int, default=30)
    mk.add_argument("--pdf-only", action="store_true", help="AI 없이 저장된 원고로 PDF만 다시 만들기")
    ft = sp.add_parser("fitness", help="회원 운동·식단 관리표 생성 (fitness/members.json → fitness/routines/)")
    ft.add_argument("--check", action="store_true", help="데이터 오류만 검사")
    rc = sp.add_parser("record", help="(내부용) 명령 결과를 앱에 기록")
    rc.add_argument("status"); rc.add_argument("file"); rc.add_argument("label", nargs="?", default="")

    for c in ("status", "jobs", "daily", "export"):
        sp.add_parser(c)
    x = ap.parse_args(argv)

    if x.cmd == "run":
        review, rp = mother.run(x.goal)
        p(review["summary"], "\n다음:", *[f"\n- {a}" for a in review["next_actions"]], f"\n보고서: {rp.relative_to(store.ROOT)}")
    elif x.cmd == "ask":
        p(agents.run(x.agent, x.task))
    elif x.cmd == "agent":
        if x.action == "list":
            for n, s_ in agents.all_agents().items():
                avg, _ = agents.score(n)
                p(f"{n:16} v{s_.get('version', 1)} {s_.get('title', '')} " + (f"({avg:.1f}점)" if avg else ""))
        elif x.action == "new":
            p(json.dumps(agents.create(x.name, x.arg), ensure_ascii=False, indent=1))
        elif x.action == "upgrade":
            names = [x.name] if x.name else list(agents.all_agents())
            for n in names:
                u = agents.upgrade(n, force=x.force)
                p(f"{n}: " + (f"v{u['version']} 업그레이드" if u else "유지"))
        elif x.action == "add-skill":
            spec = agents.load(x.name)
            spec.setdefault("skills", []).append(x.arg)
            agents.save(spec)
            p(f"{x.name} ← 스킬 {x.arg}")
    elif x.cmd == "search":
        k, q = x.kind, x.query
        if k == "google":
            p(tools.google_search(q, x.lang, x.region))
        elif k in ("github", "code"):
            p(tools.github_search(q, "repos" if k == "github" else "code"))
        elif k in ("skills", "prompts", "agents"):
            p(tools.github_search(q, k))
        else:
            p(tools.youtube_search(q, x.region, trending=(k == "trending")))
    elif x.cmd == "fitness":
        from . import fitness
        if x.check:
            errs = fitness.validate(fitness.load())
            p("\n".join(errs) or "오류 없음")
        else:
            out, n = fitness.export_all()
            p(f"회원 {n}명 관리표 생성 → {out.relative_to(store.ROOT)}")
    elif x.cmd == "crawl":
        p(tools.crawl(x.url))
    elif x.cmd == "skill":
        p(tools.import_skill(x.repo, x.path))
        if x.agent:
            name = sorted(store.SKILLS.glob("*.md"), key=lambda f: f.stat().st_mtime)[-1].stem
            spec = agents.load(x.agent)
            spec.setdefault("skills", []).append(name)
            agents.save(spec)
            p(f"{x.agent} ← 스킬 {name}")
    elif x.cmd == "biz":
        if x.action == "scout":
            for i in business.scout(x.market):
                p(f"{i['id']} {i['score']}점 [{i['status']}] {i['market']}/{i['platform']} {i['title']}\n   → {i['first_step']}")
        elif x.action == "list":
            for i in store.load_json("ideas.json", []):
                p(f"{i['id']} {i['score']}점 [{i['status']}] {i['market']} {i['title']}")
        elif x.action == "approve":
            business.approve(x.id); p(f"{x.id} 진행 시작")
        elif x.action == "log":
            business.log(x.id, x.revenue, x.cost, x.currency, x.note); p("기록됨")
        elif x.action == "review":
            rows, plans = business.review()
            for it, m, act in rows:
                p(f"{it['id']} {act.upper()} ROI {m['roi']:+.0%} 매출 ${m['revenue']} | {plans.get(it['id'], {}).get('plan', '')}")
            p("진행중 사업 없음" if not rows else "")
    elif x.cmd == "ai":
        if x.action == "status":
            p(providers.status())
        elif x.action == "check":
            p("\n".join(providers.check_all()))
        elif x.action == "ask":
            text, used = providers.complete(x.prompt, spec={"tier": "worker", "tools": [], "model": x.model})
            p(text, f"\n— {used}")
        else:
            for mid, sc, why in providers.arena(x.prompt):
                p(f"{sc:>2}점 {mid} — {why}")
    elif x.cmd == "status":
        p(cmd_status())
    elif x.cmd == "jobs":
        p(cmd_jobs())
    elif x.cmd == "daily":
        p(cmd_daily())
    elif x.cmd == "news":
        from . import collector
        if x.query == "add":
            p(collector.add_source(x.url))
        elif x.query == "discover":
            p("새 출처: " + (", ".join(collector.discover()) or "없음"))
        elif x.query == "sources":
            for s_ in collector._sources():
                p(("❌ " if s_.get("removed") else "✅ ") + f"{s_['name']} [{s_['category']}] {s_['origin']} · {s_['url']}")
        elif x.query:
            p(collector.search(x.query))
        else:
            added, failed = collector.collect()
            p(f"새 소식 {added}건 수집" + (f" · 실패 {len(failed)}곳" if failed else ""))
    elif x.cmd == "hook":
        p(tools.hook_score(x.text, x.title, x.thumb))
    elif x.cmd == "pipeline":
        from . import pipelines
        if x.action == "new":
            pp = pipelines.create(x.arg)
            p(f"⚙️ 파이프라인 생성: {pp['title']} [{pp['schedule']}] · {len(pp['steps'])}단계"
              + (f"\n새 팀: {', '.join(pp['agents_created'])}" if pp["agents_created"] else "")
              + (f"\n장착 스킬: {', '.join(pp['skills_equipped'])}" if pp["skills_equipped"] else "")
              + (f"\n🧪 {'생존' if pp['viability']['pass'] else '탈락(꺼짐)'}: {pp['viability']['why']}" if pp.get("viability") else "")
              + f"\n바로 실행: pipeline run {pp['name']}")
        elif x.action == "list":
            for pp in pipelines.all_pipes():
                p(f"{'✅' if pp.get('enabled') else '⏸'} {pp['name']} [{pp['schedule']}] {pp['title']} · 실행 {len(pp.get('runs', []))}회")
        elif x.action == "run":
            for label, out in pipelines.run(x.arg):
                p(f"▶ {label}\n{out[:800]}\n")
        else:
            pp = pipelines.load(x.arg)
            pp["enabled"] = x.action == "on"
            pipelines.save(pp)
            p(f"{pp['name']}: {'켜짐' if pp['enabled'] else '꺼짐'}")
    elif x.cmd == "test":
        from . import viability
        if x.target == "all":
            p("\n".join(viability.test_all()) or "테스트할 대상 없음")
        else:
            if x.target == "pipeline":
                _, r = viability.test_pipeline(x.name)
            else:
                ideas = store.load_json("ideas.json", [])
                for i in ideas:  # 탈락한 사업을 직접 테스트하면 '살리기' 시도: 후보로 되돌리고 개선 루프부터
                    if i["id"] == x.target and i["status"] == "killed":
                        i["status"], i["killed_by"] = "candidate", None
                        store.save_json("ideas.json", ideas)
                idea, r = viability.test_idea(x.target)
                for u in idea.get("upgrades", [])[-_ROUNDS():]:
                    if u.get("title"):
                        p(f"🔧 개선 {u['round']}차: {u['title']} → {'생존' if u['pass'] else '채택' if u['adopted'] else '버림'} ({u['result']})")
            sm = r["sim"]
            p(f"{'✅ 생존' if r['pass'] else '⏸ 보류' if r.get('hold') else '❌ 탈락'} — {r['why']}\n90일 매출 P10/P50/P90: ${sm['rev_p10']}/${sm['rev_p50']}/${sm['rev_p90']} · 손익분기 {sm['breakeven_p50']}일"
              + "\n" + "\n".join(f"- {e['role']} {e['model']}: 가격 ${e['price_usd']} 전환 {e['conv_rate_pct']}% 하루 {e['visitors_low']}~{e['visitors_high']}" for e in r["estimates"]))
    elif x.cmd == "shorts":
        from . import publish
        p(publish.skip(x.skip) if x.skip else publish.shorts(private=x.private, topic=x.topic))
    elif x.cmd == "story":
        from . import story
        if x.action == "list":
            p("\n".join(f"- {b['slug']}: {b['title']} ({len(b['made'])}화)" for b in story.all_series()) or "시리즈 없음")
        elif x.action == "new":
            b, log = story.new_series(x.arg, x.genre)
            p("\n".join(log))
            p(story.episode(b["slug"], x.private))
        else:
            slug = x.arg or (story.all_series() or [{}])[-1].get("slug", "")
            p(story.plan_episode(slug)[1] if x.action == "plan" else story.episode(slug, x.private))
    elif x.cmd == "order":
        from . import orders
        p(orders.make(x.service, x.request))
    elif x.cmd == "benchmark":
        from . import benchmark
        d = benchmark.refresh()
        p(benchmark.brief(10) or "수집 결과 없음(유튜브 키 확인)")
    elif x.cmd == "blog":
        from . import publish
        p(publish.blog())
    elif x.cmd == "make":
        from . import product
        if x.pdf_only:
            p("📕 PDF 다시 만듦: " + str(product.rebuild_pdf(x.id) or "실패(원고 없음)"))
            return
        r = product.make(x.id, x.pages)
        p(f"📦 상품 완성: {r['title']} · {r['sections']}장 · {r['chars']:,}자" + (" · PDF" if r["pdf"] else "")
          + f" · 만든 AI {', '.join(r['models'])}\n보고서: {r['report']}")
    elif x.cmd == "record":
        import pathlib
        f = pathlib.Path(x.file)
        out = f.read_text(encoding="utf-8", errors="replace").strip() if f.exists() else ""
        store.append_jsonl("commands.jsonl", {"ts": store.now().isoformat(timespec="seconds"), "cmd": x.label[:200],
                                              "ok": x.status == "0", "output": out[-3000:] or "(출력 없음)"})
    elif x.cmd == "export":
        from . import dashboard
        d = dashboard.build()
        p(f"앱 데이터 갱신: 사업 {len(d['ideas'])} · 팀 {len(d['team'])} · 보고서 {len(d['reports'])}")


RETRYABLE = ("Timeout", "ConnectionError", "APIConnectionError", "RateLimitError", "InternalServerError",
             "OverloadedError", "ServiceUnavailable")


def safe_main(argv=None, wait=10):
    """에러 자동 처리: 일시 오류는 1회 자동 재시도 → 그래도 실패하면 기록 남기고 한 줄 보고."""
    import time
    import traceback
    for attempt in (1, 2):
        try:
            return main(argv)
        except llm.BudgetExceeded as e:
            sys.exit(f"⚠️ {e}")
        except SystemExit:
            raise
        except Exception as e:
            name = type(e).__name__
            store.append_jsonl("errors.jsonl", {"ts": store.now().isoformat(timespec="seconds"),
                                                "cmd": " ".join(argv or sys.argv[1:]), "error": f"{name}: {e}"[:500],
                                                "trace": traceback.format_exc()[-1500:], "attempt": attempt})
            if attempt == 1 and any(k in name for k in RETRYABLE):
                time.sleep(wait)
                continue
            sys.exit(store.redact(f"⚠️ 실패: {name}: {str(e)[:150]} (기록: data/errors.jsonl)"))


if __name__ == "__main__":
    safe_main()
