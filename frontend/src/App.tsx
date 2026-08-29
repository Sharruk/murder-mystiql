import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  BadgeCheck,
  BarChart3,
  BookOpen,
  Braces,
  ChevronRight,
  CircleHelp,
  Clock3,
  Code2,
  Copy,
  Database,
  ExternalLink,
  FileCode2,
  Flag,
  Github,
  KeyRound,
  Layers3,
  LockKeyhole,
  Menu,
  Play,
  RefreshCw,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  Terminal,
  TimerReset,
  Trophy,
  Users,
  X,
  Zap,
} from "lucide-react";
import { api } from "./api";
import type { GameState, InvestigationTable, LeaderboardEntry, QueryResult, Screen } from "./types";

const SESSION_KEY = "murder-mystiql-session";
const emptyQuery = "SELECT\n  1 AS ready;";

function formatTime(totalSeconds: number) {
  const seconds = Math.max(0, totalSeconds);
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const rest = seconds % 60;
  return [hours, minutes, rest].map((value) => String(value).padStart(2, "0")).join(":");
}

function formatMs(value: number) {
  return `${value}ms`;
}

function App() {
  const [screen, setScreen] = useState<Screen>("landing");
  const [session, setSession] = useState<GameState | null>(null);
  const [teamName, setTeamName] = useState("");
  const [showJoin, setShowJoin] = useState(false);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");
  const [workspaceError, setWorkspaceError] = useState("");
  const [query, setQuery] = useState(emptyQuery);
  const [queryLoading, setQueryLoading] = useState(false);
  const [queryResult, setQueryResult] = useState<QueryResult | null>(null);
  const [tables, setTables] = useState<InvestigationTable[]>([]);
  const [lockedTableCount, setLockedTableCount] = useState(0);
  const [answer, setAnswer] = useState("");
  const [answerLoading, setAnswerLoading] = useState(false);
  const [answerMessage, setAnswerMessage] = useState<{ tone: "success" | "error"; text: string } | null>(null);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [menuOpen, setMenuOpen] = useState(false);
  const [now, setNow] = useState(Date.now());

  const refreshSession = useCallback(async (sessionId: string) => {
    try {
      const result = await api.state(sessionId);
      setSession(result.session);
      return result.session;
    } catch {
      localStorage.removeItem(SESSION_KEY);
      setSession(null);
      return null;
    }
  }, []);

  useEffect(() => {
    const stored = localStorage.getItem(SESSION_KEY);
    if (stored) {
      refreshSession(stored).then((result) => {
        if (result) setScreen("workspace");
        setLoading(false);
      });
    } else {
      setLoading(false);
    }
  }, [refreshSession]);

  useEffect(() => {
    if (!session || screen !== "workspace") return;
    const interval = window.setInterval(() => {
      setNow(Date.now());
      refreshSession(session.session_id);
    }, 1000);
    return () => window.clearInterval(interval);
  }, [refreshSession, screen, session?.session_id]);

  useEffect(() => {
    if (!session || screen !== "workspace") return;
    api.tables(session.session_id).then((result) => {
      setTables(result.available_tables);
      setLockedTableCount(result.locked_table_count);
    }).catch(() => {
      setTables([]);
      setLockedTableCount(0);
    });
  }, [session?.session_id, screen, session?.current_level_number]);

  const elapsedSeconds = useMemo(() => {
    if (!session) return 0;
    if (session.finish_at) return session.actual_duration_seconds;
    return session.actual_duration_seconds + Math.max(0, Math.floor((now - Date.now()) / 1000));
  }, [now, session]);

  const startGame = async () => {
    setError("");
    setStarting(true);
    try {
      const result = await api.start(teamName);
      setSession(result.session);
      localStorage.setItem(SESSION_KEY, result.session.session_id);
      setShowJoin(false);
      setScreen("workspace");
      setTeamName("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start the investigation.");
    } finally {
      setStarting(false);
    }
  };

  const runQuery = async () => {
    if (!session) return;
    setWorkspaceError("");
    setQueryLoading(true);
    try {
      const result = await api.query(session.session_id, query);
      setQueryResult(result);
    } catch (err) {
      setQueryResult(null);
      setWorkspaceError(err instanceof Error ? err.message : "Query could not be completed.");
    } finally {
      setQueryLoading(false);
    }
  };

  const submitAnswer = async () => {
    if (!session) return;
    setWorkspaceError("");
    setAnswerMessage(null);
    setAnswerLoading(true);
    try {
      const result = await api.answer(session.session_id, answer);
      setSession(result.state);
      setAnswer("");
      setAnswerMessage(
        result.correct
          ? { tone: "success", text: result.state.status === "COMPLETED" ? "Investigation complete." : "Correct. Next level unlocked." }
          : { tone: "error", text: `Not quite. ${Math.round(result.penalty_seconds / 60)} minute penalty applied.` },
      );
    } catch (err) {
      setWorkspaceError(err instanceof Error ? err.message : "Answer could not be submitted.");
    } finally {
      setAnswerLoading(false);
    }
  };

  const openLeaderboard = async () => {
    setScreen("leaderboard");
    setMenuOpen(false);
    try {
      const result = await api.leaderboard();
      setLeaderboard(result.entries);
    } catch {
      setLeaderboard([]);
    }
  };

  const leaveSession = async () => {
    if (session && session.status === "IN_PROGRESS") {
      await api.finish(session.session_id).catch(() => undefined);
    }
    localStorage.removeItem(SESSION_KEY);
    setSession(null);
    setScreen("landing");
    setMenuOpen(false);
  };

  if (loading) return <div className="loading-screen"><div className="loading-mark">M<span>/</span>M</div><div className="loader-line" /></div>;

  return (
    <div className="app-shell">
      <div className="noise-layer" />
      <Header
        screen={screen}
        session={session}
        onHome={() => { setScreen(session ? "workspace" : "landing"); setMenuOpen(false); }}
        onLeaderboard={openLeaderboard}
        onOrganizer={() => { setScreen("organizer"); setMenuOpen(false); }}
        menuOpen={menuOpen}
        setMenuOpen={setMenuOpen}
        onLeave={leaveSession}
      />

      <main>
        {screen === "landing" && (
          <Landing onEnter={() => setShowJoin(true)} onLeaderboard={openLeaderboard} />
        )}
        {screen === "workspace" && session && (
          <Workspace
            session={session}
            elapsedSeconds={elapsedSeconds}
            tables={tables}
            lockedTableCount={lockedTableCount}
            query={query}
            setQuery={setQuery}
            queryResult={queryResult}
            queryLoading={queryLoading}
            workspaceError={workspaceError}
            onRunQuery={runQuery}
            onClearQuery={() => { setQuery(""); setQueryResult(null); setWorkspaceError(""); }}
            answer={answer}
            setAnswer={setAnswer}
            answerLoading={answerLoading}
            answerMessage={answerMessage}
            onSubmitAnswer={submitAnswer}
          />
        )}
        {screen === "leaderboard" && <Leaderboard entries={leaderboard} onBack={() => setScreen(session ? "workspace" : "landing")} />}
        {screen === "organizer" && <Organizer onBack={() => setScreen(session ? "workspace" : "landing")} />}
      </main>

      {showJoin && (
        <JoinModal
          teamName={teamName}
          setTeamName={setTeamName}
          loading={starting}
          error={error}
          onClose={() => { setShowJoin(false); setError(""); }}
          onSubmit={startGame}
        />
      )}
    </div>
  );
}

function Header({ screen, session, onHome, onLeaderboard, onOrganizer, menuOpen, setMenuOpen, onLeave }: {
  screen: Screen; session: GameState | null; onHome: () => void; onLeaderboard: () => void; onOrganizer: () => void;
  menuOpen: boolean; setMenuOpen: (value: boolean) => void; onLeave: () => void;
}) {
  return (
    <header className="topbar">
      <button className="brand" onClick={onHome} aria-label="Go to home">
        <span className="brand-mark">M<span>/</span>M</span>
        <span className="brand-copy"><strong>MURDER MYSTIQL</strong><small>INVESTIGATION ENGINE</small></span>
      </button>
      <div className="topbar-right">
        {session && screen === "workspace" && (
          <div className="session-chip"><span className="live-dot" /> LIVE SESSION <b>{session.team_name}</b></div>
        )}
        <button className="quiet-button desktop-only" onClick={onLeaderboard}><Trophy size={15} /> Leaderboard</button>
        <button className="quiet-button desktop-only" onClick={onOrganizer}><Layers3 size={15} /> Organizer</button>
        <button className="menu-trigger" onClick={() => setMenuOpen(!menuOpen)} aria-label="Open menu"><Menu size={18} /></button>
        {menuOpen && (
          <div className="menu-popover">
            <button onClick={onLeaderboard}><Trophy size={15} /> Leaderboard</button>
            <button onClick={onOrganizer}><Layers3 size={15} /> Organizer console</button>
            {session && <button onClick={onLeave} className="danger-text"><X size={15} /> End session</button>}
          </div>
        )}
      </div>
    </header>
  );
}

function Landing({ onEnter, onLeaderboard }: { onEnter: () => void; onLeaderboard: () => void }) {
  return (
    <div className="landing page-wrap">
      <section className="hero">
        <div className="hero-eyebrow"><span className="eyebrow-mark">◎</span> EVENT INVESTIGATION PLATFORM <span className="eyebrow-rule" /></div>
        <h1>Find the signal<br /><em>in the noise.</em></h1>
        <p className="hero-copy">A configurable investigation engine for live events. Query the evidence, connect the dots, and let your case take shape.</p>
        <div className="hero-actions">
          <button className="primary-button large" onClick={onEnter}><Play size={16} fill="currentColor" /> Enter investigation <ArrowRight size={16} /></button>
          <button className="text-button" onClick={onLeaderboard}>View leaderboard <ChevronRight size={15} /></button>
        </div>
        <div className="hero-footnote"><ShieldCheck size={14} /> Anonymous session · Server-authoritative game state</div>
      </section>
      <section className="engine-preview">
        <div className="preview-header"><span>ENGINE / READY</span><span className="preview-status"><span className="live-dot" /> awaiting case configuration</span></div>
        <div className="preview-grid">
          <div className="preview-rail">
            <div className="rail-label">CASE FILE</div>
            <div className="rail-empty"><FileCode2 size={20} /><span>No case<br />configured</span></div>
            <div className="rail-line active" /><div className="rail-line" /><div className="rail-line" />
          </div>
          <div className="preview-terminal">
            <div className="terminal-bar"><span className="terminal-dots"><i /><i /><i /></span><span><Terminal size={13} /> QUERY TERMINAL</span><small>READ ONLY</small></div>
            <div className="code-lines">
              <div><span className="line-no">01</span><span className="syntax-key">SELECT</span><span className="syntax-muted"> &nbsp;signal, context</span></div>
              <div><span className="line-no">02</span><span className="syntax-key">FROM</span><span className="syntax-muted"> &nbsp;your_investigation</span></div>
              <div><span className="line-no">03</span><span className="syntax-key">WHERE</span><span className="syntax-muted"> &nbsp;the_truth = </span><span className="syntax-string">'out_there'</span><span className="cursor-blink">▋</span></div>
              <div><span className="line-no">04</span></div>
            </div>
            <div className="preview-result"><span><span className="result-dot" /> 0 rows</span><span>waiting for configuration</span></div>
          </div>
          <div className="preview-schema">
            <div className="rail-label">DATABASE SCHEMA</div>
            <div className="schema-empty"><Database size={20} /><span>Tables will<br />appear here</span></div>
          </div>
        </div>
      </section>
      <section className="principles">
        <div className="section-kicker">BUILT FOR THE CASE YOU BRING</div>
        <div className="principles-grid">
          <Principle icon={<Database />} number="01" title="Query the evidence" body="A safe, read-only SQL terminal makes the investigation database your primary tool." />
          <Principle icon={<TimerReset />} number="02" title="Race the clock" body="Server-authoritative time, configurable penalties, and a leaderboard that rewards precision." />
          <Principle icon={<Braces />} number="03" title="Shape any story" body="Organizers configure levels, tables, clues, hints, and answers without rewriting the engine." />
        </div>
      </section>
      <footer className="site-footer"><span>© 2026 MURDER MYSTIQL</span><span>ENGINE BUILD 0.1 <span className="footer-separator">/</span> STORY-INDEPENDENT</span></footer>
    </div>
  );
}

function Principle({ icon, number, title, body }: { icon: React.ReactNode; number: string; title: string; body: string }) {
  return <article className="principle"><div className="principle-top"><span className="principle-icon">{icon}</span><span className="principle-number">{number}</span></div><h3>{title}</h3><p>{body}</p></article>;
}

function Workspace({ session, elapsedSeconds, tables, lockedTableCount, query, setQuery, queryResult, queryLoading, workspaceError, onRunQuery, onClearQuery, answer, setAnswer, answerLoading, answerMessage, onSubmitAnswer }: {
  session: GameState; elapsedSeconds: number; tables: InvestigationTable[]; lockedTableCount: number; query: string; setQuery: (value: string) => void;
  queryResult: QueryResult | null; queryLoading: boolean; workspaceError: string; onRunQuery: () => void; onClearQuery: () => void;
  answer: string; setAnswer: (value: string) => void; answerLoading: boolean; answerMessage: { tone: "success" | "error"; text: string } | null; onSubmitAnswer: () => void;
}) {
  const progress = session.total_levels ? Math.round((session.completed_levels / session.total_levels) * 100) : 0;
  return (
    <div className="workspace page-wrap">
      <div className="workspace-head">
        <div><div className="section-kicker">CURRENT INVESTIGATION</div><h2>{session.has_configured_case ? `Level ${session.current_level_number}` : "Engine standby"}</h2></div>
        <div className="workspace-metrics">
          <div className="metric"><Clock3 size={15} /><span>ELAPSED</span><strong>{formatTime(elapsedSeconds)}</strong></div>
          <div className="metric"><Zap size={15} /><span>EFFECTIVE</span><strong>{formatTime(session.effective_time_seconds)}</strong></div>
          <div className="metric progress-metric"><span>PROGRESS</span><strong>{progress}%</strong><div className="mini-progress"><i style={{ width: `${progress}%` }} /></div></div>
        </div>
      </div>
      <div className="workspace-grid">
        <aside className="side-column left-column">
          <div className="panel-label"><BookOpen size={14} /> CASE FILE <span className="panel-label-line" /></div>
          {session.current_level ? <div className="case-content"><div className="level-chip">LEVEL {String(session.current_level_number).padStart(2, "0")}</div><h3>{session.current_level.title}</h3><p>{session.current_level.description || "This level is ready for your investigation."}</p><div className="clue-box"><div className="clue-label"><Sparkles size={13} /> CURRENT CLUE</div><p>{session.current_level.clue || "No clue has been configured for this level."}</p></div></div> : <EmptyPanel icon={<FileCode2 />} title="No case configured" body="The investigation engine is ready. An organizer must configure a case before levels and clues can appear." />}
          <div className="progress-card"><div className="progress-card-head"><span>INVESTIGATION PROGRESS</span><strong>{session.completed_levels}/{session.total_levels || "—"}</strong></div><div className="progress-track"><i style={{ width: `${progress}%` }} /></div><div className="progress-steps"><span className="done">START</span><span className={progress ? "active" : ""}>DISCOVER</span><span>RESOLVE</span></div></div>
        </aside>
        <section className="center-column">
          <div className="panel-label"><Terminal size={14} /> SQL TERMINAL <span className="panel-label-line" /><span className="read-only"><LockKeyhole size={11} /> READ ONLY</span></div>
          <div className="terminal-panel">
            <div className="terminal-toolbar"><div className="terminal-title"><span className="terminal-dots"><i /><i /><i /></span><span>investigation.sql</span></div><div className="terminal-actions"><button onClick={onClearQuery}><RefreshCw size={13} /> Clear</button><button className="run-button" onClick={onRunQuery} disabled={queryLoading}><Play size={13} fill="currentColor" /> {queryLoading ? "Running..." : "Run query"} <span className="shortcut">⌘ ↵</span></button></div></div>
            <div className="editor-wrap"><div className="editor-gutter">{query.split("\n").map((_, index) => <span key={index}>{String(index + 1).padStart(2, "0")}</span>)}</div><textarea value={query} onChange={(event) => setQuery(event.target.value)} spellCheck={false} aria-label="SQL query editor" placeholder="Write a read-only SELECT query..." onKeyDown={(event) => { if ((event.metaKey || event.ctrlKey) && event.key === "Enter") { event.preventDefault(); onRunQuery(); } }} /></div>
            <div className="terminal-footer"><span><span className="status-dot" /> Connection ready</span><span>⌘ ↵ to run</span></div>
          </div>
          <div className="results-heading"><span className="panel-label"><BarChart3 size={14} /> QUERY RESULTS</span>{queryResult && <span className="result-meta">{queryResult.row_count} rows <i /> {formatMs(queryResult.duration_ms)}</span>}</div>
          <div className="results-panel">{workspaceError ? <div className="inline-error"><CircleHelp size={16} /><span>{workspaceError}</span></div> : queryResult ? <ResultTable result={queryResult} /> : <div className="results-empty"><Search size={22} /><h3>Run a query to inspect results</h3><p>Query execution and answer submission are separate actions. Explore as much as you need.</p></div>}</div>
          <div className="answer-panel"><div className="answer-copy"><div className="answer-icon"><KeyRound size={17} /></div><div><div className="panel-label">SUBMIT FINDING</div><h3>{session.has_configured_case ? "What did you uncover?" : "Answer submission is offline"}</h3><p>{session.has_configured_case ? "Submit your conclusion when you’re ready. Wrong answers incur the configured event penalty." : "Answers become available when an organizer adds investigation levels."}</p></div></div><div className="answer-form"><input value={answer} onChange={(event) => setAnswer(event.target.value)} disabled={!session.has_configured_case || answerLoading} onKeyDown={(event) => { if (event.key === "Enter") onSubmitAnswer(); }} placeholder="Enter your answer..." /><button onClick={onSubmitAnswer} disabled={!session.has_configured_case || answerLoading || !answer.trim()}>{answerLoading ? <RefreshCw className="spin" size={15} /> : <Send size={15} />} Submit answer</button></div>{answerMessage && <div className={`answer-feedback ${answerMessage.tone}`}><BadgeCheck size={15} /> {answerMessage.text}</div>}</div>
        </section>
        <aside className="side-column right-column">
          <div className="panel-label"><Database size={14} /> DATABASE SCHEMA <span className="panel-label-line" /></div>
          <div className="schema-panel"><div className="schema-panel-head"><span>AVAILABLE TABLES</span><strong>{tables.length}</strong></div>{tables.length ? tables.map((table) => <TableItem table={table} key={table.name} />) : <div className="schema-empty-panel"><Database size={18} /><span>No investigation tables<br />configured yet.</span></div>}<div className="schema-panel-head locked-head"><span>LOCKED TABLES</span><strong>{lockedTableCount}</strong></div>{lockedTableCount ? <div className="locked-note"><LockKeyhole size={14} /> Tables unlock as you progress.</div> : <div className="locked-note muted"><LockKeyhole size={14} /> No locked tables to show.</div>}</div>
          <Cheatsheet />
        </aside>
      </div>
    </div>
  );
}

function TableItem({ table }: { table: InvestigationTable }) {
  return <details className="table-item"><summary><span className="table-icon"><Database size={13} /></span><span>{table.label || table.name}</span><ChevronRight size={14} /></summary><div className="column-list">{table.columns.map((column) => <div key={column.name}><span>{column.name}{column.is_primary_key && <KeyRound size={10} />}</span><small>{column.data_type}</small></div>)}</div></details>;
}

function ResultTable({ result }: { result: QueryResult }) {
  return result.rows.length ? <div className="result-table-wrap"><table><thead><tr>{result.columns.map((column) => <th key={column}>{column}</th>)}</tr></thead><tbody>{result.rows.map((row, rowIndex) => <tr key={rowIndex}>{row.map((cell, cellIndex) => <td key={cellIndex}>{String(cell)}</td>)}</tr>)}</tbody></table></div> : <div className="results-empty compact"><Search size={20} /><h3>Query returned no rows</h3><p>The query ran successfully. No configured records matched.</p></div>;
}

function Cheatsheet() {
  const snippets = ["SELECT · WHERE · AND / OR", "LIKE · IN · BETWEEN", "ORDER BY · GROUP BY · HAVING", "COUNT · SUM · AVG · MIN · MAX", "JOIN · INNER JOIN · LEFT JOIN", "Aliases · subqueries · CTEs"];
  return <details className="cheatsheet"><summary><span><Code2 size={14} /> SQL CHEATSHEET</span><ChevronRight size={14} /></summary><div>{snippets.map((snippet) => <p key={snippet}>{snippet}</p>)}</div></details>;
}

function EmptyPanel({ icon, title, body }: { icon: React.ReactNode; title: string; body: string }) {
  return <div className="empty-panel"><div className="empty-icon">{icon}</div><h3>{title}</h3><p>{body}</p></div>;
}

function Leaderboard({ entries, onBack }: { entries: LeaderboardEntry[]; onBack: () => void }) {
  return <div className="simple-page page-wrap"><button className="back-link" onClick={onBack}><ChevronRight size={15} className="rotate-180" /> Back to {entries.length ? "investigation" : "home"}</button><div className="simple-heading"><div className="section-kicker"><Trophy size={13} /> LIVE RANKINGS</div><h1>Precision under pressure.</h1><p>Completed investigations are ranked by effective time. Configure your first case to bring the board to life.</p></div><div className="leaderboard-card">{entries.length ? <><div className="leaderboard-head"><span>RANK</span><span>TEAM</span><span>PROGRESS</span><span>EFFECTIVE TIME</span><span>STATUS</span></div>{entries.map((entry) => <div className="leaderboard-row" key={`${entry.team_name}-${entry.rank}`}><strong>#{String(entry.rank).padStart(2, "0")}</strong><span className="team-cell"><span className="team-avatar">{entry.team_name.slice(0, 1).toUpperCase()}</span>{entry.team_name}</span><span><div className="row-progress"><i style={{ width: `${entry.progress_percent}%` }} /></div>{entry.progress_percent}%</span><span className="mono">{formatTime(entry.effective_time_seconds)}</span><span className={`status-pill ${entry.status.toLowerCase()}`}>{entry.status}</span></div>)}</> : <div className="leaderboard-empty"><Trophy size={25} /><h3>No teams on the board yet.</h3><p>Rankings will appear as anonymous teams enter and complete a configured investigation.</p></div>}</div></div>;
}

function Organizer({ onBack }: { onBack: () => void }) {
  const capabilities = [{ icon: <BookOpen />, title: "Case & story", body: "Connect prologue, characters, locations, evidence, and relationships." }, { icon: <Layers3 />, title: "Level builder", body: "Order levels, attach clues, configure answers, and unlock tables." }, { icon: <ShieldCheck />, title: "Event rules", body: "Set timers, wrong-answer locks, hint penalties, and lifecycle state." }, { icon: <Users />, title: "Session monitor", body: "Watch progress, leaderboard status, and export final results." }];
  return <div className="simple-page page-wrap"><button className="back-link" onClick={onBack}><ChevronRight size={15} className="rotate-180" /> Back to investigation</button><div className="simple-heading"><div className="section-kicker"><Layers3 size={13} /> ORGANIZER CONSOLE</div><h1>Shape the investigation.</h1><p>The organizer layer is intentionally separated from participant play. Configure your event here when the case is ready—without changing the game engine.</p></div><div className="organizer-status"><div className="status-orb"><Sparkles size={20} /></div><div><span className="status-label">ENGINE STATUS</span><h3>Ready for configuration</h3><p>No event content has been added. This is an intentional empty state.</p></div><span className="ready-tag"><span className="live-dot" /> READY</span></div><div className="capability-grid">{capabilities.map((item) => <article className="capability" key={item.title}><div className="capability-icon">{item.icon}</div><h3>{item.title}</h3><p>{item.body}</p><button className="disabled-link" disabled>Available when connected <LockKeyhole size={12} /></button></article>)}</div><div className="organizer-note"><ShieldCheck size={16} /><span><strong>Authentication boundary</strong> Organizer auth is intentionally left configurable so Firebase or another provider can be added later without rewriting participant game state.</span></div></div>;
}

function JoinModal({ teamName, setTeamName, loading, error, onClose, onSubmit }: { teamName: string; setTeamName: (value: string) => void; loading: boolean; error: string; onClose: () => void; onSubmit: () => void }) {
  return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><div className="join-modal"><button className="modal-close" onClick={onClose} aria-label="Close"><X size={16} /></button><div className="modal-mark"><span>M</span><i>/</i><span>M</span></div><div className="section-kicker">ANONYMOUS SESSION</div><h2>Choose your team name.</h2><p>No account required. Your session is stored securely and the clock begins when you enter.</p><label htmlFor="team-name">TEAM / DISPLAY NAME</label><input id="team-name" autoFocus value={teamName} onChange={(event) => setTeamName(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") onSubmit(); }} placeholder="e.g. The Observers" maxLength={80} />{error && <div className="modal-error"><CircleHelp size={14} /> {error}</div>}<button className="primary-button full" onClick={onSubmit} disabled={loading}>{loading ? <RefreshCw className="spin" size={16} /> : <Play size={16} fill="currentColor" />} {loading ? "Creating session..." : "Enter investigation"} <ArrowRight size={16} /></button><div className="modal-foot"><LockKeyhole size={12} /> No authentication · no account · just the case</div></div></div>;
}

export default App;