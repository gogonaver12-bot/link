// 과목: 해부학 기초 (초보자용)
(function () {
  const pm = (t) => 'https://pubmed.ncbi.nlm.nih.gov/?term=' + encodeURIComponent(t);
  const OPENSTAX = { text: 'OpenStax, Anatomy and Physiology 2e (무료 공개 교과서)', url: 'https://openstax.org/details/books/anatomy-and-physiology-2e', why: '초보자용 무료 교과서, 한 단원씩 읽기 좋음' };

  (window.SUBJECTS ||= []).push({
    id: 'anatomy',
    title: '해부학 기초',
    emoji: '🦴',
    description: '우리 몸이 어떤 부품으로 만들어졌는지 — 뼈, 근육, 심장, 폐, 소화기관.',
    lessons: [
      {
        id: 'intro',
        emoji: '🧍',
        title: '몸의 지도 읽기 (방향·단면)',
        summary: '해부학 공부의 첫걸음: 위·아래·앞·뒤를 부르는 이름.',
        analogy: '지도에 동서남북이 있듯, 몸에도 "기준 자세"와 방향 이름이 있어요.',
        body: [
          '해부학에서는 항상 "해부학적 자세"를 기준으로 말해요. 똑바로 서서, 얼굴은 앞을 보고, 손바닥이 앞을 향한 자세예요.',
          '머리 쪽은 위(상, superior), 발 쪽은 아래(하, inferior), 배 쪽은 앞(전, anterior), 등 쪽은 뒤(후, posterior)라고 해요.',
          '몸 가운데 선에 가까우면 안쪽(내측, medial), 멀면 바깥쪽(외측, lateral)이에요. 예: 엄지는 새끼손가락보다 바깥쪽!',
          '몸을 자르는 방향도 이름이 있어요. 좌우로 나누면 시상면, 앞뒤로 나누면 관상면, 위아래로 나누면 수평면(횡단면)이에요. CT·MRI 사진이 바로 이 단면들이에요.'
        ],
        figure: {
          caption: '해부학적 자세와 세 가지 단면',
          svg: `<svg viewBox="0 0 420 260" role="img" aria-label="해부학적 자세와 단면">
            <g fill="none" stroke="#3b6df0" stroke-width="3">
              <circle cx="120" cy="45" r="22"/><line x1="120" y1="67" x2="120" y2="160"/>
              <line x1="120" y1="85" x2="80" y2="140"/><line x1="120" y1="85" x2="160" y2="140"/>
              <line x1="120" y1="160" x2="95" y2="235"/><line x1="120" y1="160" x2="145" y2="235"/>
            </g>
            <line x1="120" y1="10" x2="120" y2="250" stroke="#d64545" stroke-dasharray="6 4"/>
            <line x1="40" y1="120" x2="200" y2="120" stroke="#1f9d61" stroke-dasharray="6 4"/>
            <g fill="currentColor" font-size="13">
              <text x="128" y="20">↑ 위(상)</text><text x="128" y="252">↓ 아래(하)</text>
              <text x="205" y="124">수평면</text><text x="20" y="20" fill="#d64545">시상면(좌/우)</text>
            </g>
            <g transform="translate(250,40)" fill="currentColor" font-size="13">
              <rect x="0" y="0" width="150" height="170" rx="12" fill="none" stroke="currentColor" opacity=".3"/>
              <text x="12" y="28">내측 = 가운데 쪽</text><text x="12" y="56">외측 = 바깥 쪽</text>
              <text x="12" y="84">전(앞) = 배 쪽</text><text x="12" y="112">후(뒤) = 등 쪽</text>
              <text x="12" y="140">근위 = 몸통 가까이</text><text x="12" y="162">원위 = 몸통에서 멀리</text>
            </g></svg>`
        },
        terms: [['해부학적 자세', '서서 앞을 보고 손바닥이 앞을 향한 기준 자세'], ['근위/원위', '팔다리에서 몸통에 가까운 쪽/먼 쪽 (어깨는 손목보다 근위)']],
        video: { search: ['anatomical position directional terms', '해부학 방향 용어'] },
        refs: [OPENSTAX],
        quiz: [
          { q: '손목은 팔꿈치보다 어느 쪽일까요?', options: ['근위', '원위', '내측'], answer: 1, explain: '몸통에서 더 멀리 있으니 원위예요.' },
          { q: '몸을 왼쪽·오른쪽으로 나누는 단면은?', options: ['시상면', '관상면', '수평면'], answer: 0, explain: '시상면은 좌우로 나눠요.' }
        ]
      },
      {
        id: 'bone',
        emoji: '🦴',
        title: '뼈대 (골격계)',
        summary: '206개의 뼈가 몸을 지탱하고 보호하고 피를 만들어요.',
        analogy: '뼈는 건물의 철골 구조물 + 금고(뇌·심장 보호) + 공장(골수에서 혈액 생산)이에요.',
        body: [
          '성인의 뼈는 약 206개예요. 아기는 더 많지만 자라면서 일부가 서로 붙어요.',
          '뼈가 하는 일 5가지: ① 몸 지탱 ② 장기 보호(두개골→뇌, 갈비뼈→심장·폐) ③ 근육과 함께 움직임 ④ 칼슘 저장 ⑤ 골수에서 혈구 생산.',
          '뼈와 뼈가 만나는 곳이 관절이에요. 무릎·팔꿈치처럼 많이 움직이는 관절도 있고, 두개골 이음매처럼 거의 안 움직이는 관절도 있어요.',
          '뼈는 살아 있는 조직이라 계속 부서지고 새로 만들어져요(골재형성). 그래서 부러져도 다시 붙어요.'
        ],
        figure: {
          caption: '긴뼈(예: 넙다리뼈)의 구조',
          svg: `<svg viewBox="0 0 420 240" role="img" aria-label="긴뼈 구조">
            <g transform="translate(60,20)">
              <ellipse cx="60" cy="25" rx="45" ry="25" fill="#f2e3c6" stroke="#b89a5e" stroke-width="2"/>
              <rect x="38" y="25" width="44" height="150" fill="#f2e3c6" stroke="#b89a5e" stroke-width="2"/>
              <rect x="50" y="35" width="20" height="130" fill="#e8a0a0"/>
              <ellipse cx="60" cy="178" rx="45" ry="25" fill="#f2e3c6" stroke="#b89a5e" stroke-width="2"/>
            </g>
            <g stroke="currentColor" opacity=".6"><line x1="165" y1="45" x2="230" y2="45"/><line x1="130" y1="120" x2="230" y2="110"/><line x1="145" y1="150" x2="230" y2="160"/></g>
            <g fill="currentColor" font-size="14">
              <text x="235" y="50">뼈끝(골단) — 관절을 이룸</text>
              <text x="235" y="115">골수강 — 골수(피 공장)</text>
              <text x="235" y="165">치밀뼈 — 단단한 바깥벽</text>
            </g></svg>`
        },
        terms: [['골수', '뼈 속 말랑한 조직. 적혈구·백혈구·혈소판을 만듦'], ['관절', '뼈와 뼈가 만나는 곳'], ['연골', '관절 끝을 덮은 매끈한 쿠션']],
        video: { search: ['skeletal system for beginners', '골격계 쉽게'] },
        refs: [OPENSTAX, { text: 'Drake, Vogl, Mitchell — Gray’s Anatomy for Students', why: '그림이 많은 표준 해부학 교과서' }],
        quiz: [
          { q: '성인의 뼈는 대략 몇 개?', options: ['약 106개', '약 206개', '약 306개'], answer: 1 },
          { q: '피(혈구)를 만드는 곳은?', options: ['연골', '골수', '인대'], answer: 1, explain: '뼈 속 골수가 혈구를 만들어요.' }
        ]
      },
      {
        id: 'muscle',
        emoji: '💪',
        title: '근육 (근육계)',
        summary: '근육은 "당기기"만 할 수 있어요. 밀기는 반대편 근육 담당!',
        analogy: '근육은 줄다리기 팀이에요. 한쪽(이두근)이 당기면 팔이 굽고, 반대쪽(삼두근)이 당기면 펴져요.',
        body: [
          '근육은 3종류예요. ① 골격근: 내 마음대로 움직임(팔·다리) ② 심장근: 심장만의 근육, 저절로 뜀 ③ 민무늬근: 위·장·혈관 벽, 저절로 움직임.',
          '근육은 스스로 길어질 수 없고 "짧아지며 당기기"만 해요. 그래서 굽히는 근육과 펴는 근육이 짝을 이뤄요.',
          '근육 속에는 액틴과 마이오신이라는 아주 가는 실이 있어요. 마이오신이 액틴을 노 젓듯 끌어당겨 서로 미끄러지며 근육이 짧아져요. 이것을 "활주설(미끄럼 이론)"이라고 해요.',
          '근육은 힘줄(건)로 뼈에 붙어요. 뇌에서 신경 신호가 오면 칼슘이 나오고, 그 칼슘이 수축 스위치를 켜요.'
        ],
        figure: {
          caption: '팔 굽히기: 이두근 수축, 삼두근 이완',
          svg: `<svg viewBox="0 0 420 220" role="img" aria-label="이두근과 삼두근">
            <g stroke="#b89a5e" stroke-width="10" stroke-linecap="round"><line x1="80" y1="40" x2="200" y2="140"/><line x1="200" y1="140" x2="330" y2="70"/></g>
            <path d="M95 40 Q160 40 205 125" fill="#e86a6a" opacity=".85"/>
            <path d="M90 60 Q130 150 195 150" fill="#e8a0a0" opacity=".7"/>
            <g fill="currentColor" font-size="14">
              <text x="120" y="30">이두근: 수축(짧아짐) → 당김</text>
              <text x="60" y="185">삼두근: 이완(늘어남)</text>
              <text x="300" y="60">아래팔 ↑</text>
            </g></svg>`
        },
        terms: [['골격근', '뜻대로 움직이는 근육'], ['힘줄(건)', '근육을 뼈에 붙이는 질긴 끈'], ['액틴/마이오신', '근육 수축을 만드는 두 단백질 실']],
        video: { search: ['sliding filament theory animation', '근육 수축 원리 애니메이션'] },
        refs: [
          OPENSTAX,
          { text: 'Huxley HE, Hanson J (1954) Nature 173:973 — 근육 수축의 활주설', url: pm('Huxley Hanson 1954 changes in the cross-striations of muscle during contraction'), why: '활주설을 처음 보여준 고전 논문' },
          { text: 'Huxley AF, Niedergerke R (1954) Nature 173:971', url: pm('Huxley Niedergerke 1954 structural changes in muscle during contraction'), why: '같은 해 독립적으로 발표된 활주설 논문' }
        ],
        quiz: [
          { q: '심장을 이루는 근육은?', options: ['골격근', '심장근', '민무늬근'], answer: 1 },
          { q: '근육이 할 수 있는 동작은?', options: ['당기기만', '밀기만', '당기기와 밀기 모두'], answer: 0, explain: '근육은 짧아지며 당기기만 해요. 그래서 짝 근육이 필요해요.' }
        ]
      },
      {
        id: 'heart',
        emoji: '❤️',
        title: '심장과 혈액순환',
        summary: '심장은 두 개의 펌프가 붙어 있는 구조예요.',
        analogy: '심장은 2층 집 두 채가 붙은 펌프장이에요. 오른쪽 집은 피를 폐로, 왼쪽 집은 온몸으로 보내요.',
        body: [
          '심장은 방 4개: 우심방·우심실·좌심방·좌심실. "방"은 피를 받는 곳, "실"은 피를 내보내는 곳이에요.',
          '① 온몸을 돈 피(산소 부족) → 우심방 → 우심실 → 폐동맥 → 폐에서 산소 충전. ② 폐에서 온 피(산소 풍부) → 좌심방 → 좌심실 → 대동맥 → 온몸.',
          '좌심실은 온몸으로 피를 보내야 해서 벽이 가장 두꺼워요.',
          '판막은 한쪽으로만 열리는 문이라 피가 거꾸로 흐르지 않아요. "쿵-닥" 심장 소리는 판막이 닫히는 소리예요.',
          '피가 몸을 "순환"한다는 사실은 1628년 윌리엄 하비가 처음 실험으로 증명했어요.'
        ],
        figure: {
          caption: '심장의 4개 방과 피의 흐름 (파랑=산소 부족, 빨강=산소 풍부)',
          svg: `<svg viewBox="0 0 420 260" role="img" aria-label="심장 구조">
            <rect x="90" y="40" width="110" height="80" rx="14" fill="#5b8def" opacity=".8"/>
            <rect x="210" y="40" width="110" height="80" rx="14" fill="#e86a6a" opacity=".8"/>
            <rect x="90" y="128" width="110" height="100" rx="14" fill="#3b6df0" opacity=".85"/>
            <rect x="210" y="128" width="110" height="100" rx="14" fill="#d64545" opacity=".85"/>
            <g fill="#fff" font-size="15" font-weight="700" text-anchor="middle">
              <text x="145" y="85">우심방</text><text x="265" y="85">좌심방</text>
              <text x="145" y="182">우심실</text><text x="265" y="182">좌심실</text>
            </g>
            <g fill="currentColor" font-size="13">
              <text x="5" y="70">온몸에서 →</text><text x="5" y="200">→ 폐로</text>
              <text x="328" y="70">← 폐에서</text><text x="328" y="200">온몸으로 →</text>
              <text x="120" y="250">※ 그림의 왼쪽 = 몸의 오른쪽</text>
            </g></svg>`
        },
        terms: [['동맥', '심장에서 나가는 혈관'], ['정맥', '심장으로 들어오는 혈관'], ['판막', '피가 거꾸로 못 가게 막는 문']],
        video: { search: ['blood flow through the heart animation', '심장 혈액순환 쉽게'] },
        refs: [OPENSTAX, { text: 'William Harvey (1628) De Motu Cordis — 혈액순환의 발견', why: '혈액이 순환한다는 것을 처음 증명한 역사적 저작' }],
        quiz: [
          { q: '온몸으로 피를 보내는 방은?', options: ['우심실', '좌심실', '우심방'], answer: 1 },
          { q: '판막의 역할은?', options: ['피를 만든다', '피의 역류를 막는다', '산소를 넣는다'], answer: 1 }
        ]
      },
      {
        id: 'lung',
        emoji: '🫁',
        title: '호흡 (폐)',
        summary: '산소는 들이고 이산화탄소는 내보내요.',
        analogy: '폐 속 허파꽈리는 수억 개의 작은 풍선이에요. 풍선 벽 너머로 산소와 이산화탄소가 자리를 바꿔요.',
        body: [
          '공기 길: 코 → 인두 → 후두 → 기관 → 기관지 → 세기관지 → 허파꽈리(폐포).',
          '숨쉬기의 주인공은 가로막(횡격막)이에요. 가로막이 아래로 내려가면 가슴 공간이 커져 공기가 빨려 들어와요(들숨). 올라가면 공기가 나가요(날숨).',
          '허파꽈리는 약 3~5억 개, 펼치면 테니스장 크기 정도 넓어요. 벽이 아주 얇아서 산소가 피로, 이산화탄소가 공기로 쉽게 이동해요(확산).'
        ],
        figure: {
          caption: '공기 길과 허파꽈리',
          svg: `<svg viewBox="0 0 420 240" role="img" aria-label="호흡기">
            <g fill="none" stroke="#3b6df0" stroke-width="6" stroke-linecap="round">
              <line x1="150" y1="20" x2="150" y2="100"/><path d="M150 100 Q120 120 90 160"/><path d="M150 100 Q180 120 210 160"/>
              <path d="M90 160 L70 190 M90 160 L105 195"/><path d="M210 160 L230 190 M210 160 L195 195"/>
            </g>
            <g fill="#e86a6a" opacity=".8"><circle cx="68" cy="198" r="9"/><circle cx="106" cy="203" r="9"/><circle cx="232" cy="198" r="9"/><circle cx="194" cy="203" r="9"/></g>
            <path d="M40 225 Q150 205 260 225" stroke="#1f9d61" stroke-width="4" fill="none"/>
            <g fill="currentColor" font-size="13">
              <text x="160" y="40">기관</text><text x="215" y="130">기관지</text>
              <text x="250" y="200">허파꽈리(폐포)</text><text x="270" y="232" fill="#1f9d61">가로막</text>
            </g>
            <g transform="translate(300,40)" fill="currentColor" font-size="13">
              <text x="0" y="0">허파꽈리에서:</text><text x="0" y="22">O₂ → 혈액</text><text x="0" y="44">CO₂ → 공기</text>
            </g></svg>`
        },
        terms: [['허파꽈리(폐포)', '가스 교환이 일어나는 작은 공기주머니'], ['가로막(횡격막)', '가슴과 배 사이 근육, 호흡의 주 엔진'], ['확산', '많은 곳 → 적은 곳으로 저절로 퍼지는 현상']],
        video: { search: ['how lungs work animation', '폐 호흡 원리'] },
        refs: [OPENSTAX, { text: 'West JB — Respiratory Physiology: The Essentials', why: '호흡생리 입문의 표준 교재' }],
        quiz: [
          { q: '가스 교환이 일어나는 곳은?', options: ['기관', '허파꽈리', '후두'], answer: 1 },
          { q: '들숨 때 가로막은?', options: ['위로 올라감', '아래로 내려감', '그대로'], answer: 1 }
        ]
      },
      {
        id: 'digest',
        emoji: '🍽️',
        title: '소화 (소화계)',
        summary: '음식을 잘게 부숴 피로 흡수하는 9m 길이의 터널.',
        analogy: '소화관은 입에서 항문까지 이어진 "분해 공장 컨베이어 벨트"예요.',
        body: [
          '순서: 입 → 식도 → 위 → 작은창자(소장) → 큰창자(대장) → 항문.',
          '입: 이로 부수고 침이 녹말을 분해 시작. 위: 강한 산(위산)과 효소로 단백질 분해, 음식을 죽처럼 만듦.',
          '작은창자: 영양소 흡수의 대부분이 일어나는 곳. 안쪽 벽의 수많은 융털이 면적을 넓혀요. 간(쓸개즙)과 이자(췌장, 소화효소)가 도와요.',
          '큰창자: 물을 흡수하고 남은 찌꺼기를 대변으로 만들어요. 장내 세균도 여기 많이 살아요.'
        ],
        figure: {
          caption: '소화관의 순서',
          svg: `<svg viewBox="0 0 420 240" role="img" aria-label="소화계">
            <g font-size="14" text-anchor="middle">
              ${['입', '식도', '위', '소장', '대장', '항문'].map((t, i) => `<rect x="${10 + i * 68}" y="90" width="58" height="48" rx="10" fill="#3b6df0" opacity="${0.4 + i * 0.1}"/><text x="${39 + i * 68}" y="120" fill="#fff" font-weight="700">${t}</text>`).join('')}
            </g>
            <g fill="currentColor" font-size="12" text-anchor="middle">
              <text x="39" y="160">씹기·침</text><text x="175" y="160">위산</text><text x="243" y="160">흡수 ★</text><text x="311" y="160">물 흡수</text>
              <text x="210" y="60">간(쓸개즙) · 이자(효소) → 소장으로</text>
            </g></svg>`
        },
        terms: [['융털', '소장 벽의 손가락 모양 돌기, 흡수 면적 확대'], ['쓸개즙', '간에서 만들어 지방 소화를 도움'], ['이자(췌장)', '소화효소와 인슐린을 만드는 기관']],
        video: { search: ['digestive system for kids', '소화기관 쉽게 설명'] },
        refs: [OPENSTAX],
        quiz: [
          { q: '영양소 흡수가 가장 많이 일어나는 곳?', options: ['위', '작은창자', '큰창자'], answer: 1 },
          { q: '큰창자의 주된 일은?', options: ['물 흡수', '단백질 분해', '쓸개즙 생산'], answer: 0 }
        ]
      }
    ]
  });
})();
