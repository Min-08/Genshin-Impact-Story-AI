import { useEffect, useMemo, useState } from "react";

const views = ["home", "progress", "answer", "search", "evidence"];

const recentHome = [
  ["Celestia의 진짜 목적은?", "오전 11:32"],
  ["Teyvat 대륙의 기원과 역사", "어제"],
  ["Focalors의 몰락 심마리", "2일 전"],
  ["카엔리아 멸망의 진실", "3일 전"],
  ["여행자의 정체와 운명", "3일 전"],
  ["Primordial One의 정체", "5일 전"],
  ["하늘의 못과 티바트의 인간", "6일 전"],
  ["폰타인 재판의 진짜 목적", "7일 전"],
];

const chatGroups = [
  {
    label: "오늘",
    items: [
      "Celestia의 진짜 목적은?",
      "Teyvat 대륙의 잃어버린 역사",
      "Focalors와 물의 심판 추구성",
    ],
  },
  {
    label: "어제",
    items: ["카엔리아 왕국의 멸망 원인", "여행자의 정체(사진) 정체 추측"],
  },
  {
    label: "지난 7일",
    items: ["Primordial One의 정체", "하늘의 못과 티바트의 인간 고리", "마안별 헤이모리 숨겨진 목적"],
  },
  {
    label: "지난 30일",
    items: ["Celestia의 별 바다와 관계", "7신의 권능 융합 연구"],
  },
];

function getInitialView() {
  const hash = window.location.hash.replace("#", "");
  return views.includes(hash) ? hash : "home";
}

export default function App() {
  const [view, setView] = useState(getInitialView);

  useEffect(() => {
    const onHashChange = () => setView(getInitialView());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  const screen = useMemo(() => {
    switch (view) {
      case "progress":
        return <ProgressScreen />;
      case "answer":
        return <AnswerScreen />;
      case "search":
        return <SearchScreen />;
      case "evidence":
        return <EvidenceScreen />;
      default:
        return <HomeScreen />;
    }
  }, [view]);

  const go = (nextView) => {
    window.location.hash = nextView;
    setView(nextView);
  };

  return (
    <div className={`aurora-app aurora-app--${view}`}>
      <Sidebar view={view} onNavigate={go} />
      <main className="workspace">{screen}</main>
    </div>
  );
}

function Sidebar({ view, onNavigate }) {
  const isHome = view === "home";

  return (
    <aside className="sidebar">
      <div className="brand-block">
        <Compass className="brand-symbol" />
        <div className="brand-name">Aurora</div>
        <div className="brand-subtitle">원신 스토리 추적 및 혼원 연구 시스템</div>
      </div>

      <button className="new-research" onClick={() => onNavigate("home")}>
        <Icon name="plus" />
        <span>새 연구 시작</span>
      </button>

      {isHome ? <RecentResearchHome /> : <ResearchHistory />}

      <div className="profile-card">
        <div className="profile-left">
          <div className="profile-logo">
            <Compass />
          </div>
          <div>
            <div className="profile-name">연구자</div>
            <button className="profile-mode">
              연구자 모드
              <Icon name="chevronDown" />
            </button>
          </div>
        </div>
        <button className="settings-button" aria-label="설정">
          <Icon name="settings" />
        </button>
      </div>
    </aside>
  );
}

function RecentResearchHome() {
  return (
    <section className="history-section history-section--home">
      <div className="history-heading">
        <span>최근 연구</span>
        <Icon name="search" />
      </div>
      <div className="home-list">
        {recentHome.map(([title, date], index) => (
          <button className="home-history-row" key={title}>
            <Icon name="file" />
            <span className="home-history-text">
              <strong>{title}</strong>
              <em>{date}</em>
            </span>
            <Icon name="more" />
          </button>
        ))}
      </div>
    </section>
  );
}

function ResearchHistory() {
  return (
    <section className="history-section">
      <div className="history-heading">
        <span>연구 기록</span>
        <Icon name="search" />
      </div>
      {chatGroups.map((group) => (
        <div className="history-group" key={group.label}>
          <div className="history-label">{group.label}</div>
          {group.items.map((item, index) => (
            <button className={`history-row ${index === 0 && group.label === "오늘" ? "is-active" : ""}`} key={item}>
              <Icon name="bubble" />
              <span>{item}</span>
              {index === 0 && group.label === "오늘" ? <Icon name="more" /> : null}
            </button>
          ))}
        </div>
      ))}
    </section>
  );
}

function HomeScreen() {
  return (
    <section className="home-screen">
      <div className="hero-mark">
        <Compass />
      </div>
      <h1>무엇을 연구할까요?</h1>
      <p>
        원신 세계관의 진실을 함께 추적합니다.
        <br />
        전승, 퀘스트, 캐릭터, 모순까지 - 모든 단서를 연결해 드릴게요.
      </p>

      <div className="prompt-grid">
        <PromptCard icon="spark" title="Celestia의 목적 분석">
          Celestia의 진짜 목적과 하늘의 뜻을 추적해 보세요.
        </PromptCard>
        <PromptCard icon="clock" title="카엔리아 멸망 원인">
          금지된 지식과 심연의 충돌, 그 진실을 파헤쳐 보세요.
        </PromptCard>
        <PromptCard icon="user" title="여행자와 Descender 관계">
          여행자의 기원과 Descender로서의 의미를 분석해 보세요.
        </PromptCard>
        <PromptCard icon="scales" title="폰타인 재판 기록 정리">
          폰타인 재판의 전망과 숨겨진 의도를 정리해 보세요.
        </PromptCard>
      </div>

      <Composer />
    </section>
  );
}

function PromptCard({ icon, title, children }) {
  return (
    <button className="prompt-card">
      <div className="prompt-card-title">
        <Icon name={icon} />
        <strong>{title}</strong>
      </div>
      <p>{children}</p>
      <Icon name="arrowRight" />
    </button>
  );
}

function ProgressScreen() {
  return (
    <section className="chat-screen chat-screen--progress">
      <UserBubble />
      <AssistantIdentity />

      <div className="progress-track">
        <ProgressStep active title="DB 검색 중" detail="관련 데이터 소스 탐색 중..." />
        <ProgressStep title="문헌 대조 중" detail="신뢰 문헌 및 정합성 검토 중..." />
        <ProgressStep title="추론 구조 생성 중" detail="핵심 가설과 논리 구조 정리 중..." />
      </div>

      <div className="research-status">
        <h2>연구 진행 상황</h2>
        <TimelineRow active text="관련 키워드 데이터베이스 검색 중" width="100%" />
        <TimelineRow text="신뢰 가능한 문헌 및 기록 선별 중" width="78%" />
        <TimelineRow text="핵심 개념 및 상관 관계 분석 중" width="68%" />
        <TimelineRow text="가설 구조 및 논거 생성 준비 중" width="50%" />
      </div>

      <SourcesPreview />
      <div className="result-note">
        <Icon name="spark" />
        연구 결과는 사실 확인이 필요한 가설을 포함할 수 있습니다.
      </div>
      <Composer generating />
    </section>
  );
}

function ProgressStep({ active, title, detail }) {
  return (
    <div className={`progress-step ${active ? "is-active" : ""}`}>
      <span className="step-dot" />
      <div>
        <strong>{title}</strong>
        <p>{detail}</p>
      </div>
    </div>
  );
}

function TimelineRow({ active, text, width }) {
  return (
    <div className={`timeline-row ${active ? "is-active" : ""}`}>
      <span className="timeline-dot" />
      <div className="timeline-copy">
        <strong>{text}</strong>
        <span className="timeline-bar" style={{ "--bar-width": width }} />
      </div>
    </div>
  );
}

function SourcesPreview() {
  const sources = [
    ["데이터베이스", "Celestia 운영 기록 · 관리 프로토콜", "천상 관리청 비공개 아카이브", "신뢰도 높음"],
    ["문헌", "하늘과 땅의 권능 질서 제3권", "바르카 연대기 · 제9장", "신뢰도 높음"],
    ["기록", "Focalors 재판 기록 원본", "심판정 공식 기록 보관소", "신뢰도 중간"],
  ];

  return (
    <section className="source-preview">
      <h2>검색된 주요 출처 (3)</h2>
      <div className="source-card-row">
        {sources.map(([type, title, source, trust]) => (
          <article className="source-card" key={title}>
            <span className="source-type">{type}</span>
            <strong>{title}</strong>
            <p>{source}</p>
            <em>{trust}</em>
          </article>
        ))}
        <button className="source-next" aria-label="다음 출처">
          <Icon name="chevronRight" />
        </button>
      </div>
    </section>
  );
}

function AnswerScreen() {
  return (
    <section className="chat-screen">
      <UserBubble />
      <AssistantIdentity chips />

      <AnswerParagraph />
      <div className="soft-divider" />

      <section className="summary-block">
        <div className="section-title-row">
          <h2>추론 요약</h2>
          <Icon name="chevronDown" />
        </div>
        <ul>
          <li>Celestia는 질서·계약·운명으로 원소의 흐름을 감시하고 조정합니다.</li>
          <li>하늘의 못, 신의 권좌 봉인, 여행자의 기록 등 행동 패턴은 권능 제어와 관련이 깊습니다.</li>
          <li>'이세계 격리' 목적은 별 바다와의 단절, 창세의 원리를 유지하기 위한 선택으로 해석됩니다.</li>
        </ul>
      </section>

      <ReferenceCards />
      <EvidenceRows compact />
      <Composer />
    </section>
  );
}

function SearchScreen() {
  return (
    <section className="chat-screen chat-screen--search">
      <UserBubble />
      <AssistantIdentity chips />

      <div className="search-panel">
        <div className="search-box">
          <Icon name="search" />
          <span>Celestia 목적 권능 연결</span>
          <Icon name="close" />
        </div>
        <div className="filter-row">
          <Filter label="모든 유형" />
          <Filter label="모든 출처" />
          <Filter label="모든 시대" />
          <Filter label="관련도 순" sort />
          <button className="filter-icon" aria-label="필터">
            <Icon name="filter" />
          </button>
        </div>
        <div className="source-chip-row">
          <SourceChip tone="blue" icon="bubble" label="Dialogue DB" />
          <SourceChip tone="orange" icon="circle" label="Quest Logs" />
          <SourceChip tone="green" icon="link" label="Artifact Texts" />
          <SourceChip tone="purple" icon="spark" label="Amber Archive" />
          <SourceChip tone="blue" icon="download" label="Character Notes" />
          <SourceChip tone="plain" label="더보기 +" />
        </div>
      </div>

      <div className="result-toolbar">
        <span>검색 결과 24개</span>
        <div>
          <button className="view-toggle is-active">
            <Icon name="grid" />
            카드 보기
          </button>
          <button className="view-toggle">
            <Icon name="list" />
            목록 보기
          </button>
        </div>
      </div>

      <SearchResults />
      <div className="more-note">더 많은 결과가 있습니다. 스크롤하거나 필터를 좁혀보세요. <Icon name="chevronDown" /></div>
      <Composer />
    </section>
  );
}

function EvidenceScreen() {
  return (
    <section className="chat-screen chat-screen--evidence">
      <UserBubble />
      <AssistantIdentity chips />
      <AnswerParagraph />
      <div className="soft-divider" />
      <EvidenceRows expanded />
      <Composer />
    </section>
  );
}

function UserBubble() {
  return (
    <div className="user-bubble">
      <div className="bubble-meta">
        <strong>You</strong>
        <span>오전 11:32</span>
      </div>
      <p>Celestia의 진짜 목적은 무엇일까? 티바트의 권능과 연결지어 설명해줘.</p>
    </div>
  );
}

function AssistantIdentity({ chips = false }) {
  return (
    <div className={`assistant-area ${chips ? "assistant-area--chips" : ""}`}>
      <div className="assistant-row">
        <div className="assistant-logo">
          <Compass />
        </div>
        <strong>Aurora AI</strong>
        <span>오전 11:32</span>
      </div>
      {chips ? (
        <div className="tool-chips">
          <ToolChip tone="green" icon="circle" label="DB" />
          <ToolChip tone="blue" icon="search" label="검색" />
          <ToolChip tone="purple" icon="shield" label="연구 모드" />
        </div>
      ) : null}
    </div>
  );
}

function ToolChip({ icon, label, tone }) {
  return (
    <span className={`tool-chip tool-chip--${tone}`}>
      <Icon name={icon} />
      {label}
    </span>
  );
}

function AnswerParagraph() {
  return (
    <p className="answer-copy">
      Celestia는 질서 유지를 명분으로 티바트의 권능(원소의 힘)을 통제하고 조정하는 기구로 보입니다.
      단순한 수호자가 아니라, 원초 질서의 균규성 - '이세계'와 '원리로부터 티바트를 격리' - 라는 더 근본적인 목표를 추구하는 가능성이 큽니다.
    </p>
  );
}

function ReferenceCards() {
  const cards = [
    ["선죄와 하늘 기록", "천실을 넘는 하늘 질서를 보존하며 연결되는 Celestia의 통치 기구.", "개념"],
    ["여행자 관찰 사진 해석본", "여행자 관점에서 바라본 권능과 천리 그리고 천무의 흐름.", "분석본"],
    ["별 깎는 아이 탐구 문서", "별 깎는 아이 교리를 통해 부정한 권리의 실연이 나타난 가로다.", "기록"],
    ["Focalors 자료 기록", "자판아 바루, 신들의 재판에서 드러난 권능의 제한 방식.", "주문"],
  ];

  return (
    <section className="reference-section">
      <div className="section-title-row section-title-row--left">
        <h2>출처 (4)</h2>
        <Icon name="info" />
      </div>
      <div className="reference-grid">
        {cards.map(([title, text, tag]) => (
          <article className="reference-card" key={title}>
            <div className="reference-icon">
              <Icon name="file" />
            </div>
            <strong>{title}</strong>
            <p>{text}</p>
            <span>{tag}</span>
          </article>
        ))}
        <button className="source-next source-next--reference" aria-label="다음 출처">
          <Icon name="chevronRight" />
        </button>
      </div>
    </section>
  );
}

function EvidenceRows({ compact = false, expanded = false }) {
  const rows = [
    ["Evidence 01", "선죄와 하늘 기록 문헌 구조"],
    ["Evidence 02", "티바트 원소 흐름과의 연대 기록"],
    ["Evidence 03", "기이함 주기는 존재 권리 정황"],
    ["Evidence 04", "Focalors 자료 기록"],
  ];
  const visibleRows = compact ? rows.slice(0, 3) : rows;

  return (
    <section className={`evidence-section ${compact ? "evidence-section--compact" : ""}`}>
      {expanded ? (
        <div className="section-title-row section-title-row--left">
          <h2>출처 (4)</h2>
          <Icon name="info" />
        </div>
      ) : null}
      {visibleRows.map(([label, title], index) => (
        <article className={`evidence-row ${expanded && index === 2 ? "is-expanded" : ""}`} key={label}>
          <div className="evidence-head">
            <div>
              <Icon name="file" />
              <strong>{label}</strong>
              <span>{title}</span>
            </div>
            <Icon name={expanded && index === 2 ? "chevronUp" : "chevronDown"} />
          </div>
          {expanded && index === 2 ? <ExpandedEvidence /> : null}
        </article>
      ))}
    </section>
  );
}

function ExpandedEvidence() {
  return (
    <div className="expanded-evidence">
      <div className="manuscript">
        <div className="manuscript-meta">
          <strong>기이함 주기는 존재 권리 정황</strong>
          <span>게임 내 문헌</span>
          <em>획득: 자유의 심장 임무 중</em>
          <i>원문 언어: 티바트 고대어</i>
          <i>기록 일자: 불명</i>
        </div>
        <blockquote>
          "... 만물은 주기의 흐름 속에서 태어나고, 기이함은 그 주기를 벗어난다.
          <br />
          <br />
          기이함이 누적되면, 세계는 불안정해지고 질서는 무너진다.
          <br />
          <mark>이에 하늘은 내려와, 그 흐름을 바로잡고, 존재의 권리를 다시 수여한다.'</mark>
          <br />
          <mark>그렇게 하여, 세계는 다시 균형을 찾고, 새로운 순환이 시작된다.'</mark>
          <br />
          ..."
        </blockquote>
      </div>
      <aside className="research-note">
        <div>
          <strong>연구 노트</strong>
          <Icon name="edit" />
        </div>
        <p>
          기이함 = 원소의 과잉, 혹은 금지된 지식의 축적을 의미할 가능성이 높음.
          Celestia는 이를 제거하거나 초기화하여 티바트의 질서를 재설정하는 역할 수행.
        </p>
        <footer>
          <span>메모 작성자: 연구자</span>
          <span>오늘 오전 11:35</span>
        </footer>
      </aside>
    </div>
  );
}

function SearchResults() {
  const results = [
    ["Dialogue DB", "천리의 대화 · 제4막", "“... 천리는 말하길, 하늘은 모든 것을 지켜보고 기록하며, 그 기록은 돌아갈 곳을 알고 있다...”", "출처: 리월 · 천리", "3.2 버전", "blue"],
    ["Quest Logs", "「하늘의 못」 관련 기록", "하늘에서 떨어진 못은 하늘의 질서를 거스른 증거. 그 안에는 세계를 조정하는 힘이 봉인되어 있다.", "출처: 월드 임무 · 하늘의 못", "1.1 버전", "orange"],
    ["Artifact Texts", "시간의 모래 · 기록 III", "“... 별과 별을 잇는 자들이 있었다. 그들은 기록하고, 지우고, 다시 쓰기를 반복했다.”", "출처: 성유물 · 시간의 모래", "2.6 버전", "green"],
    ["Amber Archive", "금서 「빛의 심판」 중권", "빛은 질서를 낳고, 질서는 권능을 낳는다. 권능은 결국, 하늘의 뜻으로 귀결된다.", "출처: 앰버 아카이브 · 금서", "연대 미상", "purple"],
    ["Dialogue DB", "방랑자와 페이몬의 대화", "페이몬: “하늘이 우리를 보고 있는 걸까?” 방랑자: “그보다, 우리는 무엇을 위해 존재하지?”", "출처: 메인 스토리 · 방랑자", "3.3 버전", "blue"],
    ["Artifact Texts", "이상한 깃털 · 해설", "깃털은 하늘의 사자를 의미하며, 그들이 남긴 것은 메시지이자 경고였다.", "출처: 성유물 · 이상한 깃털", "1.3 버전", "green"],
  ];

  return (
    <div className="search-results">
      {results.map(([type, title, quote, source, version, tone]) => (
        <article className={`result-card result-card--${tone}`} key={title}>
          <div className="result-card-top">
            <span>
              <Icon name={tone === "green" ? "link" : "file"} />
              {type}
            </span>
            <Icon name="bookmark" />
          </div>
          <strong>{title}</strong>
          <p>{quote}</p>
          <footer>
            <span>{source}</span>
            <span>{version}</span>
          </footer>
        </article>
      ))}
    </div>
  );
}

function Filter({ label, sort = false }) {
  return (
    <button className={`filter-control ${sort ? "filter-control--sort" : ""}`}>
      {sort ? <Icon name="sort" /> : null}
      <span>{label}</span>
      <Icon name="chevronDown" />
    </button>
  );
}

function SourceChip({ tone, icon, label }) {
  return (
    <button className={`source-chip source-chip--${tone}`}>
      {icon ? <Icon name={icon} /> : null}
      {label}
    </button>
  );
}

function Composer({ generating = false }) {
  return (
    <div className={`composer ${generating ? "composer--generating" : ""}`}>
      <div className="composer-placeholder">메시지를 입력하세요... (Enter로 전송)</div>
      <div className="composer-bottom">
        <button className="composer-icon" aria-label="첨부">
          <Icon name="paperclip" />
        </button>
        <div className="composer-actions">
          <button className="composer-icon" aria-label="옵션">
            <Icon name="sliders" />
          </button>
          {generating ? (
            <button className="stop-button">
              <Icon name="stop" />
              생성 중단
            </button>
          ) : (
            <button className="send-button" aria-label="전송">
              <Icon name="send" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function Compass({ className = "" }) {
  return <img className={`compass ${className}`} src="/aurora-compass.png" alt="" aria-hidden="true" />;
}

function Icon({ name }) {
  const common = {
    width: 20,
    height: 20,
    viewBox: "0 0 24 24",
    fill: "none",
    xmlns: "http://www.w3.org/2000/svg",
    "aria-hidden": "true",
  };

  const paths = {
    plus: <path d="M12 5v14M5 12h14" />,
    search: <path d="m21 21-4.3-4.3M19 11a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z" />,
    settings: (
      <>
        <path d="M12 15.2a3.2 3.2 0 1 0 0-6.4 3.2 3.2 0 0 0 0 6.4Z" />
        <path d="M19.4 15a1.8 1.8 0 0 0 .36 2l.06.06a2.1 2.1 0 0 1-3 3l-.06-.06a1.8 1.8 0 0 0-2-.36 1.8 1.8 0 0 0-1.1 1.66V21.5a2.1 2.1 0 0 1-4.2 0v-.08a1.8 1.8 0 0 0-1.18-1.66 1.8 1.8 0 0 0-2 .36l-.06.06a2.1 2.1 0 1 1-3-3l.06-.06a1.8 1.8 0 0 0 .36-2 1.8 1.8 0 0 0-1.66-1.1H1.9a2.1 2.1 0 1 1 0-4.2h.08a1.8 1.8 0 0 0 1.66-1.18 1.8 1.8 0 0 0-.36-2l-.06-.06a2.1 2.1 0 0 1 3-3l.06.06a1.8 1.8 0 0 0 2 .36h.08A1.8 1.8 0 0 0 9.5 2.5v-.08a2.1 2.1 0 0 1 4.2 0v.08a1.8 1.8 0 0 0 1.1 1.66 1.8 1.8 0 0 0 2-.36l.06-.06a2.1 2.1 0 0 1 3 3l-.06.06a1.8 1.8 0 0 0-.36 2v.08a1.8 1.8 0 0 0 1.66 1.1h.08a2.1 2.1 0 1 1 0 4.2h-.08A1.8 1.8 0 0 0 19.4 15Z" />
      </>
    ),
    chevronDown: <path d="m6 9 6 6 6-6" />,
    chevronUp: <path d="m18 15-6-6-6 6" />,
    chevronRight: <path d="m9 18 6-6-6-6" />,
    arrowRight: <path d="M5 12h14m-5-5 5 5-5 5" />,
    bubble: <path d="M20 11.5a7.5 7.5 0 0 1-10.7 6.8L4 20l1.7-4.8A7.5 7.5 0 1 1 20 11.5Z" />,
    file: <path d="M6 3h8l4 4v14H6V3Zm8 0v5h5M9 13h6M9 17h5" />,
    more: (
      <>
        <circle cx="5" cy="12" r="1.2" fill="currentColor" />
        <circle cx="12" cy="12" r="1.2" fill="currentColor" />
        <circle cx="19" cy="12" r="1.2" fill="currentColor" />
      </>
    ),
    spark: <path d="M12 2 14 10l8 2-8 2-2 8-2-8-8-2 8-2 2-8Z" />,
    clock: (
      <>
        <circle cx="12" cy="12" r="8" />
        <path d="M12 7v5l3 2" />
      </>
    ),
    user: (
      <>
        <circle cx="12" cy="8" r="4" />
        <path d="M4 21a8 8 0 0 1 16 0" />
      </>
    ),
    scales: <path d="M12 3v18M5 6h14M7 6l-4 7h8L7 6Zm10 0-4 7h8l-4-7Z" />,
    paperclip: <path d="m21 12.5-8.5 8.5a6 6 0 0 1-8.5-8.5l9-9a4 4 0 0 1 5.7 5.7l-9 9a2 2 0 0 1-2.8-2.8l8.5-8.5" />,
    sliders: <path d="M4 7h10M18 7h2M4 17h2M10 17h10M14 4v6M8 14v6" />,
    send: <path d="m3 20 18-8L3 4l4 8-4 8Zm4-8h14" fill="currentColor" stroke="none" />,
    stop: <rect x="7" y="7" width="10" height="10" rx="1" />,
    circle: <circle cx="12" cy="12" r="6" />,
    shield: <path d="M12 3 20 6v5c0 5-3.4 8.6-8 10-4.6-1.4-8-5-8-10V6l8-3Z" />,
    info: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 10v7M12 7h.01" />
      </>
    ),
    close: <path d="m6 6 12 12M18 6 6 18" />,
    filter: <path d="M4 5h16l-6 7v5l-4 2v-7L4 5Z" />,
    sort: <path d="M8 5v14m0 0-3-3m3 3 3-3M16 19V5m0 0-3 3m3-3 3 3" />,
    grid: <path d="M4 4h6v6H4V4Zm10 0h6v6h-6V4ZM4 14h6v6H4v-6Zm10 0h6v6h-6v-6Z" />,
    list: <path d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01" />,
    link: <path d="M10 13a5 5 0 0 0 7 0l2-2a5 5 0 0 0-7-7l-1 1M14 11a5 5 0 0 0-7 0l-2 2a5 5 0 0 0 7 7l1-1" />,
    download: <path d="M12 4v11m0 0 4-4m-4 4-4-4M5 20h14" />,
    bookmark: <path d="M7 4h10v17l-5-3-5 3V4Z" />,
    edit: <path d="M4 20h4L19 9l-4-4L4 16v4Zm10-14 4 4" />,
  };

  return (
    <svg {...common} className={`icon icon--${name}`} stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      {paths[name]}
    </svg>
  );
}
