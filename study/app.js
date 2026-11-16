// 쉬운 공부방 - 과목 데이터(subjects/*.js)를 읽어 화면을 그립니다.
// 과목 파일은 window.SUBJECTS 배열에 객체를 push 하면 자동으로 등록됩니다.
(function () {
  const SUBJECTS = window.SUBJECTS || [];
  const app = document.getElementById('app');
  const KEY = 'study-progress-v1';

  const load = () => { try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch { return {}; } };
  const save = (p) => { try { localStorage.setItem(KEY, JSON.stringify(p)); } catch {} };
  const isDone = (s, l) => !!(load()[s] || {})[l];
  const markDone = (s, l) => { const p = load(); (p[s] ||= {})[l] = true; save(p); };
  const esc = (t) => String(t).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const doneCount = (s) => s.lessons.filter((l) => isDone(s.id, l.id)).length;

  function totalPill() {
    const all = SUBJECTS.reduce((a, s) => a + s.lessons.length, 0);
    const d = SUBJECTS.reduce((a, s) => a + doneCount(s), 0);
    document.getElementById('progress-total').textContent = `완료 ${d}/${all}`;
  }

  function home() {
    app.innerHTML = `
      <h1>무엇을 공부할까요?</h1>
      <p class="sub">처음이어도 괜찮아요. 비유 → 그림 → 영상 → 퀴즈 순서로 천천히 따라오세요.</p>
      <div class="grid">${SUBJECTS.map((s) => {
        const pct = Math.round((doneCount(s) / s.lessons.length) * 100);
        return `<a class="card" href="#/s/${s.id}">
          <div class="emoji">${s.emoji}</div><h3>${esc(s.title)}</h3>
          <div class="sub">${esc(s.description)}</div>
          <div class="bar"><i style="width:${pct}%"></i></div>
          <div class="sub" style="font-size:13px">${doneCount(s)}/${s.lessons.length} 완료</div></a>`;
      }).join('')}</div>`;
  }

  function subject(s) {
    app.innerHTML = `
      <a href="#/">← 전체 과목</a>
      <h1>${s.emoji} ${esc(s.title)}</h1>
      <p class="sub">${esc(s.description)}</p>
      <div class="grid">${s.lessons.map((l, i) => `
        <a class="card" href="#/s/${s.id}/l/${l.id}">
          <div class="emoji">${l.emoji}</div>
          <h3>${i + 1}. ${esc(l.title)}</h3>
          <div class="sub">${esc(l.summary)}</div>
          ${isDone(s.id, l.id) ? '<div class="done">✔ 완료</div>' : ''}
        </a>`).join('')}</div>`;
  }

  function video(v) {
    if (!v) return '';
    const embed = v.youtubeId
      ? `<iframe src="https://www.youtube-nocookie.com/embed/${esc(v.youtubeId)}" allowfullscreen loading="lazy" title="강의 영상"></iframe>`
      : '';
    const links = (v.search || []).map((q) =>
      `<a class="btn ghost" target="_blank" rel="noopener" href="https://www.youtube.com/results?search_query=${encodeURIComponent(q)}">▶ "${esc(q)}" 영상 찾기</a>`).join('');
    return `<h2>🎬 영상으로 보기</h2><div class="box video">${embed}${links}
      ${v.note ? `<p class="sub" style="font-size:14px">${esc(v.note)}</p>` : ''}</div>`;
  }

  function quiz(s, l) {
    if (!l.quiz || !l.quiz.length) return '';
    return `<h2>✅ 확인 퀴즈</h2><div class="box" id="quiz">${l.quiz.map((q, qi) => `
      <p><b>Q${qi + 1}. ${esc(q.q)}</b></p>
      ${q.options.map((o, oi) => `<button class="opt" data-q="${qi}" data-o="${oi}">${esc(o)}</button>`).join('')}
      <div class="explain" id="ex-${qi}"></div>`).join('')}
      <div id="quiz-result" class="sub"></div></div>`;
  }

  function lesson(s, l) {
    const idx = s.lessons.indexOf(l);
    const prev = s.lessons[idx - 1], next = s.lessons[idx + 1];
    app.innerHTML = `
      <a href="#/s/${s.id}">← ${esc(s.title)}</a>
      <h1>${l.emoji} ${esc(l.title)}</h1>
      <p class="sub">${esc(l.summary)}</p>
      <div class="box analogy"><b>💡 한 줄 비유</b><br>${esc(l.analogy)}</div>
      <h2>📖 쉽게 설명</h2>
      <div class="box">${l.body.map((p) => `<p>${esc(p)}</p>`).join('')}</div>
      ${l.figure ? `<h2>🖼️ 그림으로 보기</h2><figure class="box figure">${l.figure.svg}<figcaption>${esc(l.figure.caption)}</figcaption></figure>` : ''}
      ${l.terms ? `<h2>🔤 꼭 알아야 할 단어</h2><dl class="box terms">${l.terms.map(([t, d]) => `<dt>${esc(t)}</dt><dd>${esc(d)}</dd>`).join('')}</dl>` : ''}
      ${video(l.video)}
      ${quiz(s, l)}
      ${l.refs ? `<h2>📑 참고 교과서·논문</h2><ul class="box refs">${l.refs.map((r) => `<li>${r.url ? `<a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.text)}</a>` : esc(r.text)}${r.why ? ` <span class="sub">— ${esc(r.why)}</span>` : ''}</li>`).join('')}</ul>` : ''}
      <button class="btn" id="mark">${isDone(s.id, l.id) ? '✔ 완료됨' : '이 단원 완료하기'}</button>
      <div class="nav">
        ${prev ? `<a class="btn ghost" href="#/s/${s.id}/l/${prev.id}">← ${esc(prev.title)}</a>` : '<span></span>'}
        ${next ? `<a class="btn" href="#/s/${s.id}/l/${next.id}">${esc(next.title)} →</a>` : `<a class="btn" href="#/s/${s.id}">목록으로</a>`}
      </div>`;

    document.getElementById('mark').onclick = (e) => { markDone(s.id, l.id); e.target.textContent = '✔ 완료됨'; totalPill(); };

    const answered = {};
    app.querySelectorAll('.opt').forEach((b) => b.onclick = () => {
      const qi = +b.dataset.q, oi = +b.dataset.o, q = l.quiz[qi];
      if (qi in answered) return;
      answered[qi] = oi === q.answer;
      app.querySelectorAll(`.opt[data-q="${qi}"]`).forEach((x) => {
        if (+x.dataset.o === q.answer) x.classList.add('right');
        else if (x === b) x.classList.add('wrong');
      });
      document.getElementById('ex-' + qi).textContent = (answered[qi] ? '정답! ' : '아쉬워요. ') + (q.explain || '');
      if (Object.keys(answered).length === l.quiz.length) {
        const ok = Object.values(answered).filter(Boolean).length;
        document.getElementById('quiz-result').textContent = `결과: ${l.quiz.length}문제 중 ${ok}개 정답` + (ok === l.quiz.length ? ' 🎉 단원 완료로 기록했어요.' : ' — 위 설명을 다시 읽어 보세요.');
        if (ok === l.quiz.length) { markDone(s.id, l.id); document.getElementById('mark').textContent = '✔ 완료됨'; totalPill(); }
      }
    });
  }

  function route() {
    const [, , sid, , lid] = location.hash.split('/');
    const s = SUBJECTS.find((x) => x.id === sid);
    const l = s && s.lessons.find((x) => x.id === lid);
    if (l) lesson(s, l); else if (s) subject(s); else home();
    totalPill();
    window.scrollTo(0, 0);
  }

  window.addEventListener('hashchange', route);
  route();
})();
