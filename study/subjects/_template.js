// 새 과목 템플릿: 이 파일을 복사해 subjects/새과목.js 로 저장 → index.html 에 <script> 한 줄 추가
(function () {
  (window.SUBJECTS ||= []).push({
    id: 'my-subject',            // 주소에 쓰일 영문 id (겹치면 안 됨)
    title: '과목 이름',
    emoji: '📘',
    description: '과목 한 줄 소개',
    lessons: [
      {
        id: 'lesson-1',
        emoji: '✨',
        title: '단원 제목',
        summary: '한 줄 요약',
        analogy: '초보자용 비유 한 줄',
        body: ['문단 1', '문단 2'],
        figure: { caption: '그림 설명', svg: '<svg viewBox="0 0 400 200"><text x="20" y="100" fill="currentColor">그림</text></svg>' },
        // 이미지 파일을 쓰려면: svg: '<img src="images/파일.png" alt="설명" style="max-width:100%">'
        terms: [['용어', '뜻']],
        video: { youtubeId: '', search: ['유튜브 검색어'] }, // youtubeId 를 넣으면 화면에 바로 재생됨
        refs: [{ text: '저자 (연도) 제목', url: 'https://...', why: '왜 읽을만한지' }],
        quiz: [{ q: '질문?', options: ['보기1', '보기2', '보기3'], answer: 0, explain: '해설' }]
      }
    ]
  });
})();
