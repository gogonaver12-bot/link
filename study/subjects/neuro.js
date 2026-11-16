// 과목: 신경계 (초보자용)
(function () {
  const pm = (t) => 'https://pubmed.ncbi.nlm.nih.gov/?term=' + encodeURIComponent(t);
  const OPENSTAX = { text: 'OpenStax, Anatomy and Physiology 2e — 신경계 단원 (무료)', url: 'https://openstax.org/details/books/anatomy-and-physiology-2e' };
  const PURVES = { text: 'Purves et al., Neuroscience 2nd ed. (NCBI Bookshelf 무료 열람)', url: 'https://www.ncbi.nlm.nih.gov/books/NBK10799/', why: '신경과학 표준 교과서' };
  const KANDEL = { text: 'Kandel et al., Principles of Neural Science', why: '신경과학의 "바이블"이라 불리는 교과서 (심화용)' };

  (window.SUBJECTS ||= []).push({
    id: 'neuro',
    title: '신경계',
    emoji: '🧠',
    description: '몸의 통신망 — 뉴런, 전기 신호, 뇌, 척수, 자율신경.',
    lessons: [
      {
        id: 'overview',
        emoji: '🗺️',
        title: '신경계 큰 그림',
        summary: '중추(뇌·척수)와 말초(온몸의 신경) 두 부분으로 나뉘어요.',
        analogy: '뇌는 본사, 척수는 고속도로, 말초신경은 각 지점으로 뻗은 전화선이에요.',
        body: [
          '중추신경계(CNS) = 뇌 + 척수. 정보를 모아서 판단하고 명령을 내려요.',
          '말초신경계(PNS) = 뇌·척수 밖의 모든 신경. 감각 정보를 본사로 올리고(감각신경), 명령을 근육으로 내려요(운동신경).',
          '말초신경 중 내 뜻과 상관없이 심장·위·땀샘을 조절하는 부분을 자율신경계라고 해요.',
          '사람 뇌에는 뉴런이 약 860억 개 있다는 연구가 있어요(Azevedo 등, 2009).'
        ],
        figure: {
          caption: '신경계의 구분',
          svg: `<svg viewBox="0 0 420 220" role="img" aria-label="신경계 구분">
            <g font-size="14" text-anchor="middle">
              <rect x="150" y="10" width="120" height="40" rx="10" fill="#3b6df0"/><text x="210" y="36" fill="#fff" font-weight="700">신경계</text>
              <rect x="40" y="90" width="150" height="40" rx="10" fill="#7a5af0"/><text x="115" y="116" fill="#fff">중추: 뇌 + 척수</text>
              <rect x="230" y="90" width="150" height="40" rx="10" fill="#1f9d61"/><text x="305" y="116" fill="#fff">말초: 온몸 신경</text>
              <rect x="210" y="165" width="90" height="40" rx="10" fill="#1f9d61" opacity=".7"/><text x="255" y="190" fill="#fff">체성(뜻대로)</text>
              <rect x="310" y="165" width="100" height="40" rx="10" fill="#1f9d61" opacity=".7"/><text x="360" y="190" fill="#fff">자율(저절로)</text>
            </g>
            <g stroke="currentColor" opacity=".5" stroke-width="2"><line x1="210" y1="50" x2="115" y2="90"/><line x1="210" y1="50" x2="305" y2="90"/><line x1="305" y1="130" x2="255" y2="165"/><line x1="305" y1="130" x2="360" y2="165"/></g></svg>`
        },
        terms: [['중추신경계', '뇌와 척수'], ['말초신경계', '중추 밖의 신경들'], ['자율신경계', '내장 기관을 자동 조절']],
        video: { search: ['nervous system overview animation', '신경계 구조 쉽게'] },
        refs: [
          OPENSTAX,
          { text: 'Azevedo FA et al. (2009) J Comp Neurol 513:532–541 — 사람 뇌 뉴런 약 860억 개', url: pm('Azevedo 2009 equal numbers of neuronal and nonneuronal cells human brain'), why: '뇌세포 수를 직접 센 유명 연구' },
          PURVES
        ],
        quiz: [
          { q: '중추신경계에 속하는 것은?', options: ['뇌와 척수', '팔의 신경', '자율신경'], answer: 0 },
          { q: '심장 박동을 자동 조절하는 것은?', options: ['체성신경', '자율신경', '감각신경'], answer: 1 }
        ]
      },
      {
        id: 'neuron',
        emoji: '🔌',
        title: '뉴런 (신경세포)',
        summary: '받는 곳(가지돌기) → 처리(세포체) → 보내는 선(축삭).',
        analogy: '뉴런은 "귀(가지돌기) + 머리(세포체) + 긴 전선(축삭) + 스피커(축삭 끝)"로 된 전화기예요.',
        body: [
          '가지돌기: 나뭇가지처럼 뻗어 다른 뉴런의 신호를 받아요.',
          '세포체: 핵이 있는 본체. 받은 신호를 모아서 "보낼까 말까" 결정해요.',
          '축삭: 신호를 멀리 보내는 긴 전선. 길이가 1m가 넘는 것도 있어요(척수→발가락).',
          '말이집(미엘린): 축삭을 감싼 절연 테이프. 신호가 마디(랑비에 마디)를 건너뛰며 훨씬 빨리 가요.',
          '뉴런이 신경계의 기본 단위라는 생각(뉴런설)은 라몬 이 카할이 현미경 관찰로 주장해 1906년 노벨상을 받았어요.'
        ],
        figure: {
          caption: '뉴런의 구조',
          svg: `<svg viewBox="0 0 440 200" role="img" aria-label="뉴런 구조">
            <g stroke="#7a5af0" stroke-width="3" fill="none" stroke-linecap="round">
              <path d="M70 100 L30 60 M70 100 L25 100 M70 100 L35 145 M45 72 L30 50 M38 130 L20 140"/>
            </g>
            <circle cx="80" cy="100" r="24" fill="#7a5af0"/><circle cx="80" cy="100" r="8" fill="#fff"/>
            <line x1="104" y1="100" x2="360" y2="100" stroke="#7a5af0" stroke-width="4"/>
            <g fill="#f2c94c">${[130, 185, 240, 295].map((x) => `<rect x="${x}" y="90" width="45" height="20" rx="9"/>`).join('')}</g>
            <g stroke="#7a5af0" stroke-width="3" stroke-linecap="round"><path d="M360 100 L395 70 M360 100 L400 100 M360 100 L395 130"/></g>
            <g fill="#7a5af0"><circle cx="397" cy="68" r="5"/><circle cx="403" cy="100" r="5"/><circle cx="397" cy="132" r="5"/></g>
            <g fill="currentColor" font-size="13" text-anchor="middle">
              <text x="40" y="180">가지돌기(받기)</text><text x="80" y="60">세포체</text>
              <text x="210" y="80">말이집(절연)</text><text x="230" y="140">축삭 → 신호 방향 →</text>
              <text x="395" y="165">축삭 끝(보내기)</text>
            </g></svg>`
        },
        terms: [['가지돌기', '신호를 받는 부분'], ['축삭', '신호를 보내는 긴 줄기'], ['말이집(미엘린)', '축삭을 감싸 신호를 빠르게 하는 막']],
        video: { search: ['neuron structure animation', '뉴런 구조 쉽게'] },
        refs: [PURVES, { text: 'Santiago Ramón y Cajal — 뉴런설 (1906 노벨 생리의학상)', url: 'https://www.nobelprize.org/prizes/medicine/1906/summary/', why: '뉴런이 개별 세포임을 밝힘' }],
        quiz: [
          { q: '신호를 받는 부분은?', options: ['축삭', '가지돌기', '말이집'], answer: 1 },
          { q: '말이집의 역할은?', options: ['신호를 빠르게', '신호를 멈춤', '영양 저장'], answer: 0 }
        ]
      },
      {
        id: 'action-potential',
        emoji: '⚡',
        title: '활동전위 (전기 신호)',
        summary: '나트륨이 들어오고 칼륨이 나가며 생기는 짧은 전기 파도.',
        analogy: '도미노예요. 한 번 넘어지기 시작하면(문턱 넘음) 끝까지 같은 크기로 쭉 전달돼요. 반만 넘어지는 일은 없어요(실무율).',
        body: [
          '쉬고 있는 뉴런의 안쪽은 바깥보다 약 −70mV 정도 음(−)이에요. 이것을 휴지전위라고 해요.',
          '자극이 충분히 크면(문턱 약 −55mV) 나트륨(Na⁺) 문이 열려 Na⁺가 확 들어와요 → 안쪽이 +로 뒤집힘(탈분극).',
          '곧 칼륨(K⁺) 문이 열려 K⁺가 나가요 → 다시 −로 돌아옴(재분극). 이 전체가 약 1~2ms(1000분의 1초) 걸려요.',
          '이 원리는 호지킨과 헉슬리가 오징어의 굵은 축삭으로 실험해 1952년 수식으로 정리했고, 1963년 노벨상을 받았어요.'
        ],
        figure: {
          caption: '활동전위 그래프 (세로: 막전위 mV, 가로: 시간 ms)',
          svg: `<svg viewBox="0 0 420 240" role="img" aria-label="활동전위 그래프">
            <g stroke="currentColor" opacity=".4"><line x1="50" y1="20" x2="50" y2="210"/><line x1="50" y1="210" x2="400" y2="210"/></g>
            <line x1="50" y1="150" x2="400" y2="150" stroke="currentColor" stroke-dasharray="4 4" opacity=".3"/>
            <line x1="50" y1="125" x2="400" y2="125" stroke="#d64545" stroke-dasharray="4 4" opacity=".6"/>
            <path d="M50 150 L130 150 L150 125 L175 35 L200 120 L225 175 L260 160 L300 150 L400 150" fill="none" stroke="#3b6df0" stroke-width="3"/>
            <g fill="currentColor" font-size="12">
              <text x="6" y="154">−70</text><text x="6" y="129" fill="#d64545">−55</text><text x="12" y="40">+30</text>
              <text x="60" y="142">휴지전위</text><text x="300" y="120" fill="#d64545">문턱</text>
              <text x="55" y="60">① Na⁺ 유입(탈분극)</text><text x="205" y="80">② K⁺ 유출(재분극)</text>
              <text x="215" y="198">③ 과분극</text>
            </g></svg>`
        },
        terms: [['휴지전위', '쉬고 있을 때 막 안팎 전압 (약 −70mV)'], ['탈분극', '안쪽이 +쪽으로 변하는 것'], ['실무율', '문턱을 넘으면 항상 같은 크기로, 못 넘으면 0']],
        video: { search: ['action potential animation', '활동전위 쉽게 설명'] },
        refs: [
          { text: 'Hodgkin AL, Huxley AF (1952) J Physiol 117:500–544', url: pm('Hodgkin Huxley 1952 quantitative description of membrane current'), why: '활동전위를 수학적으로 설명한 기념비적 논문' },
          { text: '1963 노벨 생리의학상 (Eccles, Hodgkin, Huxley)', url: 'https://www.nobelprize.org/prizes/medicine/1963/summary/' },
          PURVES
        ],
        quiz: [
          { q: '탈분극 때 세포 안으로 들어오는 이온은?', options: ['K⁺', 'Na⁺', 'Cl⁻'], answer: 1 },
          { q: '"실무율"의 뜻은?', options: ['자극이 크면 신호도 커짐', '문턱을 넘으면 항상 같은 크기', '신호가 점점 약해짐'], answer: 1 }
        ]
      },
      {
        id: 'synapse',
        emoji: '🔁',
        title: '시냅스 (뉴런끼리 대화)',
        summary: '전기 → 화학물질(신경전달물질) → 다시 전기.',
        analogy: '두 뉴런 사이엔 작은 강(시냅스 틈)이 있어요. 전기는 강을 못 건너서 "쪽지(신경전달물질)"를 배에 실어 보내요.',
        body: [
          '전기 신호가 축삭 끝에 도착하면 칼슘(Ca²⁺)이 들어와요.',
          '칼슘이 신호가 되어 작은 주머니(소포) 속 신경전달물질이 틈으로 쏟아져요.',
          '다음 뉴런의 수용체가 그 물질을 받으면 다시 전기 신호가 생겨요(흥분 또는 억제).',
          '대표 신경전달물질: 글루탐산(흥분), GABA(억제), 아세틸콜린(근육 움직임), 도파민(보상·움직임), 세로토닌(기분).',
          '신경이 화학물질로 신호를 전한다는 것은 1921년 오토 뢰비가 개구리 심장 실험으로 처음 보였어요.'
        ],
        figure: {
          caption: '시냅스: 소포 → 신경전달물질 → 수용체',
          svg: `<svg viewBox="0 0 420 220" role="img" aria-label="시냅스">
            <path d="M40 20 L190 20 Q230 60 230 100 Q230 140 190 160 L40 160 Z" fill="#7a5af0" opacity=".25" stroke="#7a5af0"/>
            <path d="M270 20 L400 20 L400 200 L270 200 Q255 110 270 20 Z" fill="#1f9d61" opacity=".25" stroke="#1f9d61"/>
            <g fill="#f2c94c" stroke="#b8962e">${[[150, 60], [175, 95], [150, 125], [195, 60]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r="12"/>`).join('')}</g>
            <g fill="#e86a6a">${[[240, 70], [248, 95], [242, 120], [252, 140], [238, 150]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r="4"/>`).join('')}</g>
            <g fill="#1f9d61">${[60, 95, 130, 165].map((y) => `<rect x="262" y="${y}" width="10" height="16" rx="3"/>`).join('')}</g>
            <g fill="currentColor" font-size="13">
              <text x="50" y="185">보내는 뉴런 (축삭 끝)</text><text x="285" y="215">받는 뉴런</text>
              <text x="100" y="45">소포</text><text x="215" y="190">틈</text><text x="290" y="110">수용체</text>
            </g></svg>`
        },
        terms: [['시냅스', '뉴런과 뉴런이 만나는 곳'], ['신경전달물질', '시냅스 틈을 건너는 화학 메시지'], ['수용체', '신경전달물질을 받는 "자물쇠"']],
        video: { search: ['synapse neurotransmitter animation', '시냅스 신경전달물질 쉽게'] },
        refs: [
          { text: 'Loewi O (1921) Pflügers Archiv — 신경의 화학적 전달 발견', why: '"미주신경 물질" 실험. 1936 노벨상' },
          { text: '1936 노벨 생리의학상 (Dale, Loewi)', url: 'https://www.nobelprize.org/prizes/medicine/1936/summary/' },
          PURVES, KANDEL
        ],
        quiz: [
          { q: '신경전달물질 방출을 일으키는 이온은?', options: ['Ca²⁺', 'K⁺', 'Na⁺'], answer: 0 },
          { q: '대표적인 억제성 신경전달물질은?', options: ['글루탐산', 'GABA', '아세틸콜린'], answer: 1 }
        ]
      },
      {
        id: 'brain',
        emoji: '🧠',
        title: '뇌의 구조와 역할',
        summary: '대뇌 4개의 엽 + 소뇌 + 뇌줄기.',
        analogy: '대뇌는 회사의 부서들이에요. 앞(이마엽)=기획실, 정수리=감각팀, 옆(관자엽)=청각·기억팀, 뒤(뒤통수엽)=영상팀.',
        body: [
          '이마엽(전두엽): 계획, 판단, 성격, 그리고 움직임 명령(일차운동겉질). 말하기 영역(브로카)도 여기 있어요.',
          '마루엽(두정엽): 촉각·통증 등 몸 감각(일차체감각겉질), 공간 파악.',
          '관자엽(측두엽): 소리 듣기, 말 이해(베르니케), 기억(해마가 안쪽에 있음).',
          '뒤통수엽(후두엽): 보는 것(시각) 처리.',
          '소뇌: 균형과 동작을 부드럽게 조절. 뇌줄기: 숨쉬기·심장박동 같은 생명 유지.',
          '펜필드는 수술 중 뇌를 직접 자극해 몸 부위가 겉질에 지도처럼 배치된 것("호문쿨루스")을 그렸어요(1937).'
        ],
        figure: {
          caption: '뇌 옆모습: 4개의 엽, 소뇌, 뇌줄기 (왼쪽이 얼굴 방향)',
          svg: `<svg viewBox="0 0 420 260" role="img" aria-label="뇌의 엽">
            <path d="M60 140 Q50 50 160 35 L190 35 L175 150 Q110 175 60 140 Z" fill="#3b6df0" opacity=".75"/>
            <path d="M190 35 Q280 30 300 90 L240 130 L175 150 Z" fill="#f2c94c" opacity=".85"/>
            <path d="M300 90 Q350 120 330 170 L260 175 L240 130 Z" fill="#e86a6a" opacity=".8"/>
            <path d="M60 140 Q110 175 175 150 L240 130 L260 175 Q200 215 120 195 Q70 180 60 140 Z" fill="#1f9d61" opacity=".75"/>
            <ellipse cx="290" cy="200" rx="45" ry="25" fill="#7a5af0" opacity=".8"/>
            <rect x="225" y="190" width="24" height="60" rx="10" fill="#a07a5a"/>
            <g fill="#fff" font-size="13" font-weight="700" text-anchor="middle">
              <text x="115" y="100">이마엽</text><text x="240" y="80">마루엽</text><text x="295" y="145">뒤통수엽</text>
              <text x="150" y="180">관자엽</text><text x="300" y="205">소뇌</text>
            </g>
            <text x="255" y="245" fill="currentColor" font-size="13">← 뇌줄기</text></svg>`
        },
        terms: [['대뇌겉질', '뇌 바깥쪽 주름진 층, 고차원 기능'], ['해마', '새 기억을 만드는 곳'], ['뇌줄기', '호흡·심장 등 생명 유지 중추']],
        video: { search: ['brain lobes and functions', '뇌 구조와 기능 쉽게'] },
        refs: [
          { text: 'Penfield W, Boldrey E (1937) Brain 60:389–443 — 운동·감각 겉질 지도(호문쿨루스)', url: pm('Penfield Boldrey 1937 somatic motor and sensory representation'), why: '뇌 지도 연구의 고전' },
          PURVES, OPENSTAX
        ],
        quiz: [
          { q: '시각을 처리하는 엽은?', options: ['이마엽', '뒤통수엽', '관자엽'], answer: 1 },
          { q: '균형과 동작 조절을 담당하는 곳은?', options: ['소뇌', '해마', '마루엽'], answer: 0 }
        ]
      },
      {
        id: 'reflex',
        emoji: '🦵',
        title: '척수와 반사',
        summary: '뜨거운 걸 만지면 뇌가 알기 전에 손이 먼저 움직여요.',
        analogy: '반사는 본사(뇌)에 보고하기 전에 현장(척수)에서 바로 처리하는 "긴급 대응 매뉴얼"이에요.',
        body: [
          '척수는 등뼈(척추) 안을 지나는 굵은 신경 다발로, 뇌와 몸을 잇는 고속도로예요.',
          '반사궁(반사 경로): ① 감각 수용기(피부) → ② 감각뉴런 → ③ 척수(사이뉴런) → ④ 운동뉴런 → ⑤ 근육.',
          '무릎 반사는 감각뉴런이 운동뉴런에 바로 연결된 가장 단순한 반사예요(단일 시냅스).',
          '반사가 뇌를 거치지 않아 아주 빨라요. 뜨거움을 "느끼는" 건 그 직후 뇌에 신호가 도착했을 때예요.',
          '셰링턴은 반사 연구로 신경계가 "통합"하며 일한다는 개념을 세웠어요(1906, 1932 노벨상).'
        ],
        figure: {
          caption: '반사궁: 피부 → 척수 → 근육',
          svg: `<svg viewBox="0 0 420 230" role="img" aria-label="반사궁">
            <ellipse cx="320" cy="110" rx="60" ry="70" fill="#7a5af0" opacity=".2" stroke="#7a5af0"/>
            <path d="M300 80 Q320 110 300 140 Q340 110 300 80" fill="#7a5af0" opacity=".5"/>
            <path d="M40 50 Q180 40 300 95" fill="none" stroke="#1f9d61" stroke-width="4"/>
            <path d="M310 120 Q200 190 70 180" fill="none" stroke="#d64545" stroke-width="4"/>
            <circle cx="40" cy="50" r="10" fill="#1f9d61"/><rect x="40" y="165" width="50" height="30" rx="12" fill="#e86a6a"/>
            <g fill="currentColor" font-size="13">
              <text x="10" y="30">① 피부(감각)</text><text x="130" y="35" fill="#1f9d61">② 감각뉴런 →</text>
              <text x="340" y="30">③ 척수</text><text x="150" y="200" fill="#d64545">← ④ 운동뉴런</text>
              <text x="20" y="220">⑤ 근육 수축</text>
            </g></svg>`
        },
        terms: [['반사', '의식하지 않고 자동으로 일어나는 빠른 반응'], ['사이뉴런(연합뉴런)', '감각뉴런과 운동뉴런을 잇는 중간 뉴런']],
        video: { search: ['reflex arc animation', '반사궁 쉽게'] },
        refs: [
          { text: 'Sherrington CS (1906) The Integrative Action of the Nervous System', why: '반사와 시냅스 개념의 고전' },
          { text: '1932 노벨 생리의학상 (Sherrington, Adrian)', url: 'https://www.nobelprize.org/prizes/medicine/1932/summary/' },
          OPENSTAX
        ],
        quiz: [
          { q: '무릎 반사를 처리하는 곳은?', options: ['대뇌', '척수', '소뇌'], answer: 1 },
          { q: '반사가 빠른 이유는?', options: ['뇌를 거치지 않아서', '근육이 커서', '혈액이 빨라서'], answer: 0 }
        ]
      },
      {
        id: 'autonomic',
        emoji: '⚖️',
        title: '자율신경 (교감 vs 부교감)',
        summary: '싸울 때 켜지는 엑셀, 쉴 때 켜지는 브레이크.',
        analogy: '교감신경 = 자동차 엑셀(위기 모드), 부교감신경 = 브레이크(휴식·소화 모드).',
        body: [
          '교감신경: 위험할 때 "싸우거나 도망가기(fight or flight)". 심장 빨라짐, 동공 커짐, 기관지 넓어짐, 소화 멈춤.',
          '부교감신경: 편할 때 "쉬고 소화하기(rest and digest)". 심장 느려짐, 동공 작아짐, 소화 활발.',
          '둘은 시소처럼 균형을 맞춰 몸 상태를 일정하게 유지해요. 이것을 항상성이라고 해요(캐넌, 1932).',
          '부교감신경의 대표는 미주신경이에요. 심장·폐·위장까지 넓게 뻗어 있어요.'
        ],
        figure: {
          caption: '교감 vs 부교감 비교',
          svg: `<svg viewBox="0 0 420 230" role="img" aria-label="교감과 부교감 비교">
            <rect x="10" y="10" width="195" height="210" rx="14" fill="#d64545" opacity=".15" stroke="#d64545"/>
            <rect x="215" y="10" width="195" height="210" rx="14" fill="#1f9d61" opacity=".15" stroke="#1f9d61"/>
            <g font-size="15" font-weight="700" text-anchor="middle"><text x="107" y="40" fill="#d64545">교감 🏃 (엑셀)</text><text x="312" y="40" fill="#1f9d61">부교감 😌 (브레이크)</text></g>
            <g fill="currentColor" font-size="14">
              ${[['심장', '빨라짐', '느려짐'], ['동공', '커짐', '작아짐'], ['기관지', '넓어짐', '좁아짐'], ['소화', '억제', '촉진'], ['침', '줄어듦', '늘어남']].map(([o, a, b], i) => `<text x="25" y="${75 + i * 30}">${o}: ${a}</text><text x="230" y="${75 + i * 30}">${o}: ${b}</text>`).join('')}
            </g></svg>`
        },
        terms: [['교감신경', '긴장·위기 대응 모드'], ['부교감신경', '휴식·회복 모드'], ['항상성', '몸 상태를 일정하게 유지하는 능력']],
        video: { search: ['sympathetic vs parasympathetic animation', '교감신경 부교감신경 차이'] },
        refs: [{ text: 'Cannon WB (1932) The Wisdom of the Body', why: '항상성·투쟁-도피 반응 개념을 정리한 고전' }, OPENSTAX, PURVES],
        quiz: [
          { q: '시험 직전 심장이 쿵쾅! 어느 신경 때문?', options: ['교감신경', '부교감신경', '감각신경'], answer: 0 },
          { q: '밥 먹고 쉴 때 활발한 것은?', options: ['교감신경', '부교감신경'], answer: 1 }
        ]
      }
    ]
  });
})();
