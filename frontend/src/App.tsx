import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  BadgeCheck,
  BarChart3,
  BookOpen,
  CheckCircle2,
  ChevronRight,
  CircleHelp,
  Clock3,
  Code2,
  Database,
  ExternalLink,
  FileCode2,
  HelpCircle,
  Info,
  KeyRound,
  Layers3,
  Lightbulb,
  LockKeyhole,
  LogIn,
  LogOut,
  Menu,
  Play,
  RefreshCw,
  Search,
  Send,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Terminal,
  TimerReset,
  Trophy,
  User as UserIcon,
  Users,
  X,
  Zap,
} from "lucide-react";
import { api, clearStoredToken, getStoredToken, setStoredToken } from "./api";
import { signInWithSSNGoogle, signOutFirebase } from "./firebase";
import type {
  GameState,
  HintItem,
  InvestigationTable,
  LeaderboardEntry,
  Participant,
  QueryResult,
  QuizQuestion,
  Screen,
} from "./types";

const DISCLAIMER_TEXT =
  "LCU: ECLIPSE is fan-made fiction created for entertainment and mystery-game purposes. It is not official canon of the Lokesh Cinematic Universe.";
const defaultQuery = "SELECT * FROM shipments LIMIT 10;";

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
  const [participant, setParticipant] = useState<Participant | null>(null);
  const [session, setSession] = useState<GameState | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [signingIn, setSigningIn] = useState(false);
  const [authError, setAuthError] = useState("");
  const [showDisclaimerModal, setShowDisclaimerModal] = useState(false);

  // Investigation Workspace State
  const [workspaceError, setWorkspaceError] = useState("");
  const [query, setQuery] = useState(defaultQuery);
  const [queryLoading, setQueryLoading] = useState(false);
  const [queryResult, setQueryResult] = useState<QueryResult | null>(null);
  const [tables, setTables] = useState<InvestigationTable[]>([]);
  const [lockedTableCount, setLockedTableCount] = useState(0);
  const [answer, setAnswer] = useState("");
  const [answerLoading, setAnswerLoading] = useState(false);
  const [answerMessage, setAnswerMessage] = useState<{ tone: "success" | "error"; text: string } | null>(null);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [organizerData, setOrganizerData] = useState<any>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [now, setNow] = useState(Date.now());
  const [activeHintPrompt, setActiveHintPrompt] = useState<HintItem | null>(null);
  const [hintLoading, setHintLoading] = useState(false);

  // Quiz State
  const [quizQuestions, setQuizQuestions] = useState<QuizQuestion[]>([]);
  const [quizAnswers, setQuizAnswers] = useState<Record<string, string>>({});
  const [quizResult, setQuizResult] = useState<{ score: number; total: number; qualified: boolean } | null>(null);

  // Check existing session on boot
  useEffect(() => {
    async function initAuth() {
      setAuthLoading(true);
      const token = getStoredToken();
      if (!token) {
        setAuthLoading(false);
        setScreen("landing");
        return;
      }
      try {
        const data = await api.getMe();
        setParticipant(data.participant);
        if (data.session) {
          setSession(data.session);
          if (data.participant.is_qualified || data.session.quiz_passed) {
            setScreen("workspace");
          } else {
            setScreen("quiz");
          }
        } else {
          // If no session exists yet, start one for this participant
          const startRes = await api.start(data.participant.display_name || "");
          setSession(startRes.session);
          if (data.participant.is_qualified || startRes.session.quiz_passed) {
            setScreen("workspace");
          } else {
            setScreen("quiz");
          }
        }
      } catch {
        clearStoredToken();
        setParticipant(null);
        setSession(null);
        setScreen("landing");
      } finally {
        setAuthLoading(false);
      }
    }
    initAuth();
  }, []);

  // Timer interval
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  const refreshSession = useCallback(async (sessionId: string) => {
    try {
      const result = await api.state(sessionId);
      setSession(result.session);
      return result.session;
    } catch (err: any) {
      console.error("Failed to refresh session:", err);
      return null;
    }
  }, []);

  const loadTables = useCallback(async (sessionId: string) => {
    try {
      const result = await api.tables(sessionId);
      setTables(result.available_tables);
      setLockedTableCount(result.locked_table_count);
    } catch {
      // Ignored
    }
  }, []);

  const loadQuizQuestions = useCallback(async () => {
    try {
      const res = await api.quizQuestions();
      setQuizQuestions(res.questions);
    } catch (err: any) {
      console.error("Failed to load quiz questions:", err);
    }
  }, []);

  // Load tables when entering workspace
  useEffect(() => {
    if (screen === "workspace" && session?.session_id) {
      loadTables(session.session_id);
    }
  }, [screen, session?.session_id, session?.current_level_number, loadTables]);

  // Load quiz questions when entering quiz screen
  useEffect(() => {
    if (screen === "quiz") {
      loadQuizQuestions();
    }
  }, [screen, loadQuizQuestions]);

  // Google Sign-In with SSN email restriction
  const handleGoogleSignIn = async () => {
    setSigningIn(true);
    setAuthError("");
    try {
      const { idToken, user } = await signInWithSSNGoogle();
      const userEmail = user.email?.toLowerCase() || "";
      if (!userEmail.endsWith("@ssn.edu.in")) {
        await signOutFirebase();
        setAuthError("Only verified SSN institutional accounts (@ssn.edu.in) can participate in MURDER MYSTIQL.");
        setSigningIn(false);
        return;
      }

      // Verify token cryptographically on FastAPI backend
      const res = await api.verifyAuth(idToken);
      setStoredToken(res.token);
      setParticipant(res.participant);
      if (res.session) {
        setSession(res.session);
      }

      if (res.participant.is_qualified || res.session?.quiz_passed) {
        setScreen("workspace");
      } else {
        setScreen("quiz");
      }
    } catch (err: any) {
      console.error("Sign-in error:", err);
      const msg = err.message || "Failed to sign in with SSN Google account.";
      setAuthError(msg.includes("invalid_domain") || msg.includes("@ssn.edu.in")
        ? "Only verified SSN institutional accounts (@ssn.edu.in) can participate in MURDER MYSTIQL."
        : msg
      );
    } finally {
      setSigningIn(false);
    }
  };

  const handleSignOut = async () => {
    try {
      await signOutFirebase();
      await api.logout().catch(() => {});
    } finally {
      clearStoredToken();
      setParticipant(null);
      setSession(null);
      setScreen("landing");
      setMenuOpen(false);
    }
  };

  const elapsedSeconds = useMemo(() => {
    if (!session?.started_at) return 0;
    const start = new Date(session.started_at).getTime();
    if (session.finish_at) {
      return Math.floor((new Date(session.finish_at).getTime() - start) / 1000);
    }
    return Math.max(0, Math.floor((now - start) / 1000));
  }, [session?.started_at, session?.finish_at, now]);

  const runQuery = async () => {
    if (!session) return;
    setQueryLoading(true);
    setWorkspaceError("");
    try {
      const result = await api.query(session.session_id, query);
      setQueryResult(result);
    } catch (err: any) {
      setQueryResult(null);
      setWorkspaceError(err.message || "Failed to execute query.");
    } finally {
      setQueryLoading(false);
    }
  };

  const submitAnswer = async () => {
    if (!session || !answer.trim()) return;
    setAnswerLoading(true);
    setAnswerMessage(null);
    try {
      const result = await api.answer(session.session_id, answer.trim());
      setSession(result.state);
      if (result.correct) {
        setAnswerMessage({
          tone: "success",
          text: result.state.status === "COMPLETED"
            ? "CORRECT! You have deduced the final showdown and solved the case!"
            : "CORRECT! Security override accepted. Next investigation level unlocked.",
        });
        setAnswer("");
        loadTables(session.session_id);
      } else {
        setAnswerMessage({
          tone: "error",
          text: `INCORRECT DEDUCTION! +5 minute penalty added. Terminal locked for ${result.lock_seconds}s.`,
        });
      }
    } catch (err: any) {
      setAnswerMessage({ tone: "error", text: err.message || "Failed to submit deduction." });
    } finally {
      setAnswerLoading(false);
    }
  };

  const requestHint = async (hintId: string) => {
    if (!session) return;
    setHintLoading(true);
    try {
      const result = await api.useHint(session.session_id, hintId);
      setSession(result.state);
      setActiveHintPrompt(null);
    } catch (err: any) {
      alert(err.message || "Failed to unlock tactical hint.");
    } finally {
      setHintLoading(false);
    }
  };

  const submitQuiz = async () => {
    if (!session) return;
    try {
      const res = await api.quizSubmit(session.session_id, quizAnswers);
      setQuizResult({ score: res.score, total: res.total_questions, qualified: res.qualified });
      setSession(res.state);
      if (participant) {
        setParticipant({ ...participant, is_qualified: res.qualified });
      }
      if (res.qualified) {
        setTimeout(() => setScreen("workspace"), 1500);
      }
    } catch (err: any) {
      alert(err.message || "Failed to submit quiz.");
    }
  };

  const openLeaderboard = async () => {
    try {
      const result = await api.leaderboard();
      setLeaderboard(result.entries);
      setScreen("leaderboard");
      setMenuOpen(false);
    } catch {
      // Ignored
    }
  };

  const openOrganizer = async () => {
    try {
      const result = await api.organizerStats();
      setOrganizerData(result);
      setScreen("organizer");
      setMenuOpen(false);
    } catch {
      // Ignored
    }
  };

  const openQuiz = () => {
    setScreen("quiz");
    setMenuOpen(false);
  };

  if (authLoading) {
    return (
      <div className="app-shell loading-shell">
        <div className="auth-spinner">
          <RefreshCw className="spin-icon" size={28} />
          <p>Authenticating SSN Credentials...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      {/* Disclaimer Sticky Notice */}
      <div className="disclaimer-banner">
        <span className="disclaimer-pill">DISCLAIMER</span>
        <span>
          LCU: ECLIPSE is <strong>fan-made fiction</strong> for Invente 2026. Not official canon.
        </span>
        <button
          className="disclaimer-link"
          onClick={() => setShowDisclaimerModal(true)}
          aria-label="Read story disclaimer"
        >
          Details
        </button>
      </div>

      <Header
        screen={screen}
        session={session}
        participant={participant}
        onHome={() => {
          if (!participant) {
            setScreen("landing");
          } else if (participant.is_qualified || session?.quiz_passed) {
            setScreen("workspace");
          } else {
            setScreen("quiz");
          }
          setMenuOpen(false);
        }}
        onLeaderboard={openLeaderboard}
        onOrganizer={openOrganizer}
        onQuiz={openQuiz}
        onSignOut={handleSignOut}
        menuOpen={menuOpen}
        setMenuOpen={setMenuOpen}
      />

      <main>
        {screen === "landing" && (
          <Landing
            signingIn={signingIn}
            authError={authError}
            participant={participant}
            onGoogleSignIn={handleGoogleSignIn}
            onEnterInvestigation={() => {
              if (participant?.is_qualified || session?.quiz_passed) {
                setScreen("workspace");
              } else {
                setScreen("quiz");
              }
            }}
            onLeaderboard={openLeaderboard}
            onQuiz={openQuiz}
          />
        )}

        {screen === "workspace" && session && (
          <Workspace
            session={session}
            participant={participant}
            elapsedSeconds={elapsedSeconds}
            tables={tables}
            lockedTableCount={lockedTableCount}
            query={query}
            setQuery={setQuery}
            queryResult={queryResult}
            queryLoading={queryLoading}
            workspaceError={workspaceError}
            onRunQuery={runQuery}
            onClearQuery={() => {
              setQuery("");
              setQueryResult(null);
              setWorkspaceError("");
            }}
            answer={answer}
            setAnswer={setAnswer}
            answerLoading={answerLoading}
            answerMessage={answerMessage}
            onSubmitAnswer={submitAnswer}
            onPromptHint={(hint) => setActiveHintPrompt(hint)}
            onSelectTable={(tableName) => {
              setQuery(`SELECT * FROM ${tableName} LIMIT 20;`);
            }}
          />
        )}

        {screen === "leaderboard" && (
          <Leaderboard
            entries={leaderboard}
            onBack={() => {
              if (!participant) setScreen("landing");
              else if (participant.is_qualified || session?.quiz_passed) setScreen("workspace");
              else setScreen("quiz");
            }}
          />
        )}

        {screen === "organizer" && (
          <Organizer
            data={organizerData}
            onBack={() => {
              if (!participant) setScreen("landing");
              else if (participant.is_qualified || session?.quiz_passed) setScreen("workspace");
              else setScreen("quiz");
            }}
          />
        )}

        {screen === "quiz" && (
          <QuizScreen
            questions={quizQuestions}
            answers={quizAnswers}
            setAnswers={setQuizAnswers}
            result={quizResult}
            session={session}
            participant={participant}
            onSubmit={submitQuiz}
            onProceed={() => setScreen("workspace")}
            onBack={() => {
              if (!participant) setScreen("landing");
              else if (participant.is_qualified || session?.quiz_passed) setScreen("workspace");
              else setScreen("landing");
            }}
          />
        )}
      </main>

      {showDisclaimerModal && (
        <DisclaimerModal onClose={() => setShowDisclaimerModal(false)} />
      )}

      {activeHintPrompt && (
        <HintConfirmModal
          hint={activeHintPrompt}
          loading={hintLoading}
          onConfirm={() => requestHint(activeHintPrompt.id)}
          onClose={() => setActiveHintPrompt(null)}
        />
      )}
    </div>
  );
}

function Header({
  screen,
  session,
  participant,
  onHome,
  onLeaderboard,
  onOrganizer,
  onQuiz,
  onSignOut,
  menuOpen,
  setMenuOpen,
}: {
  screen: Screen;
  session: GameState | null;
  participant: Participant | null;
  onHome: () => void;
  onLeaderboard: () => void;
  onOrganizer: () => void;
  onQuiz: () => void;
  onSignOut: () => void;
  menuOpen: boolean;
  setMenuOpen: (value: boolean) => void;
}) {
  return (
    <header className="topbar">
      <button className="brand" onClick={onHome} aria-label="Go to home">
        <span className="brand-mark">
          M<span>/</span>M
        </span>
        <span className="brand-copy">
          <strong>MURDER MYSTIQL</strong>
          <small>LCU: ECLIPSE · INVENTE 2026</small>
        </span>
      </button>

      <div className="topbar-right">
        {participant && (
          <div className="participant-chip desktop-only">
            <span className="live-dot" />
            <UserIcon size={13} />
            <span className="part-name">{participant.display_name || participant.email}</span>
            <span className="part-domain">@ssn.edu.in</span>
          </div>
        )}

        {session && screen === "workspace" && (
          <div className="session-chip desktop-only">
            <Layers3 size={13} /> SQUAD <b>{session.team_name}</b>
          </div>
        )}

        <button className="quiet-button desktop-only" onClick={onLeaderboard}>
          <Trophy size={15} /> Leaderboard
        </button>

        {participant && (
          <button className="quiet-button desktop-only" onClick={onQuiz}>
            <HelpCircle size={15} /> Quiz
          </button>
        )}

        <button className="quiet-button desktop-only" onClick={onOrganizer}>
          <BarChart3 size={15} /> Telemetry
        </button>

        {participant ? (
          <button className="danger-button small desktop-only" onClick={onSignOut} title="Sign Out of SSN Google Account">
            <LogOut size={14} /> Sign Out
          </button>
        ) : null}

        <button
          className="menu-button mobile-only"
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label="Toggle navigation menu"
        >
          {menuOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {menuOpen && (
        <nav className="mobile-drawer mobile-only">
          {participant && (
            <div className="mobile-user-profile">
              <UserIcon size={16} />
              <span>{participant.email}</span>
            </div>
          )}
          <button className="drawer-item" onClick={onHome}>
            <BookOpen size={16} /> Case Dossier
          </button>
          <button className="drawer-item" onClick={onLeaderboard}>
            <Trophy size={16} /> Leaderboard
          </button>
          <button className="drawer-item" onClick={onQuiz}>
            <HelpCircle size={16} /> Qualifier Quiz
          </button>
          <button className="drawer-item" onClick={onOrganizer}>
            <BarChart3 size={16} /> Organizer Telemetry
          </button>
          {participant && (
            <button className="drawer-item danger" onClick={onSignOut}>
              <LogOut size={16} /> Sign Out
            </button>
          )}
        </nav>
      )}
    </header>
  );
}

function Landing({
  signingIn,
  authError,
  participant,
  onGoogleSignIn,
  onEnterInvestigation,
  onLeaderboard,
  onQuiz,
}: {
  signingIn: boolean;
  authError: string;
  participant: Participant | null;
  onGoogleSignIn: () => void;
  onEnterInvestigation: () => void;
  onLeaderboard: () => void;
  onQuiz: () => void;
}) {
  return (
    <div className="landing page-wrap">
      <section className="hero">
        <div className="hero-eyebrow">
          <span className="eyebrow-mark">◎</span> INVENTE 2026 EVENT <span className="eyebrow-rule" />
        </div>
        <h1>
          MURDER MYSTIQL<br />
          <em>LCU: ECLIPSE</em>
        </h1>
        <p className="hero-tagline">
          Enter the investigation. Track down ghost shipments, decode intercepted transmissions, and solve the murder of the century using relational SQL.
        </p>

        {authError && (
          <div className="auth-error-banner">
            <ShieldAlert size={18} />
            <span>{authError}</span>
          </div>
        )}

        <div className="auth-card">
          {participant ? (
            <div className="authenticated-welcome">
              <div className="welcome-badge">
                <BadgeCheck size={20} /> Verified SSN Detective
              </div>
              <p className="welcome-name">
                Logged in as <strong>{participant.display_name || participant.email}</strong> ({participant.email})
              </p>
              <button className="primary-button large" onClick={onEnterInvestigation}>
                <Play size={16} fill="currentColor" /> Enter Investigation Workspace <ArrowRight size={16} />
              </button>
            </div>
          ) : (
            <div className="login-box">
              <h2 className="login-title">Enter the Investigation</h2>
              <p className="login-subtitle">
                Sign in with your verified SSN Google account to begin the investigation.
              </p>
              <button
                className="google-sign-in-button"
                onClick={onGoogleSignIn}
                disabled={signingIn}
              >
                {signingIn ? (
                  <>
                    <RefreshCw className="spin-icon" size={18} /> Verifying SSN Credentials...
                  </>
                ) : (
                  <>
                    <svg className="google-icon" viewBox="0 0 24 24" width="18" height="18">
                      <path
                        fill="#4285F4"
                        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                      />
                      <path
                        fill="#34A853"
                        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                      />
                      <path
                        fill="#FBBC05"
                        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                      />
                      <path
                        fill="#EA4335"
                        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                      />
                    </svg>
                    <span>Continue with SSN Google Account</span>
                  </>
                )}
              </button>
              <div className="login-restriction-note">
                <ShieldCheck size={14} />
                <span>Participation is restricted to verified <strong>@ssn.edu.in</strong> accounts.</span>
              </div>
            </div>
          )}
        </div>

        <div className="hero-actions">
          <button className="text-button" onClick={onLeaderboard}>
            <Trophy size={14} /> View Leaderboard
          </button>
          <button className="text-button" onClick={onQuiz}>
            <HelpCircle size={14} /> Preliminary DBMS Quiz
          </button>
        </div>
      </section>

      <section className="principles">
        <div className="section-kicker">INVESTIGATION PROTOCOLS</div>
        <div className="principles-grid">
          <Principle
            icon={<Database />}
            number="01"
            title="Relational Evidence"
            body="Query shipments, vehicle sightings, encrypted calls, wire transfers, autopsies, and forensic evidence."
          />
          <Principle
            icon={<TimerReset />}
            number="02"
            title="Penalty System"
            body="Wrong submissions add 5-minute penalties and 60-second locks. Hints add 2-minute penalties."
          />
          <Principle
            icon={<Code2 />}
            number="03"
            title="Progressive SQL"
            body="Unlock new tables and dive deeper using SELECT, JOIN, aggregates, subqueries, and timestamp filters."
          />
        </div>
      </section>

      <footer className="site-footer">
        <span>MURDER MYSTIQL · INVENTE 2026</span>
        <span>FAN-MADE FICTION · NOT OFFICIAL CANON</span>
      </footer>
    </div>
  );
}

function Principle({
  icon,
  number,
  title,
  body,
}: {
  icon: React.ReactNode;
  number: string;
  title: string;
  body: string;
}) {
  return (
    <article className="principle">
      <div className="principle-top">
        <span className="principle-icon">{icon}</span>
        <span className="principle-number">{number}</span>
      </div>
      <h3>{title}</h3>
      <p>{body}</p>
    </article>
  );
}

function Workspace({
  session,
  participant,
  elapsedSeconds,
  tables,
  lockedTableCount,
  query,
  setQuery,
  queryResult,
  queryLoading,
  workspaceError,
  onRunQuery,
  onClearQuery,
  answer,
  setAnswer,
  answerLoading,
  answerMessage,
  onSubmitAnswer,
  onPromptHint,
  onSelectTable,
}: {
  session: GameState;
  participant: Participant | null;
  elapsedSeconds: number;
  tables: InvestigationTable[];
  lockedTableCount: number;
  query: string;
  setQuery: (val: string) => void;
  queryResult: QueryResult | null;
  queryLoading: boolean;
  workspaceError: string;
  onRunQuery: () => void;
  onClearQuery: () => void;
  answer: string;
  setAnswer: (val: string) => void;
  answerLoading: boolean;
  answerMessage: { tone: "success" | "error"; text: string } | null;
  onSubmitAnswer: () => void;
  onPromptHint: (hint: HintItem) => void;
  onSelectTable: (tableName: string) => void;
}) {
  const currentLvl = session.current_level;
  const isFinished = session.status === "COMPLETED" || session.status === "FINISHED";

  return (
    <div className="workspace page-wrap">
      {/* Top Status HUD */}
      <div className="hud-bar">
        <div className="hud-metric">
          <span className="hud-label"><Clock3 size={13} /> ELAPSED TIME</span>
          <span className="hud-value font-mono">{formatTime(elapsedSeconds)}</span>
        </div>
        <div className="hud-metric">
          <span className="hud-label"><TimerReset size={13} /> PENALTIES</span>
          <span className="hud-value font-mono text-amber">
            +{formatTime(session.wrong_penalty_seconds + session.hint_penalty_seconds)}
          </span>
        </div>
        <div className="hud-metric">
          <span className="hud-label"><Sparkles size={13} /> EFFECTIVE TIME</span>
          <span className="hud-value font-mono highlight">
            {formatTime(session.effective_time_seconds)}
          </span>
        </div>
        <div className="hud-metric">
          <span className="hud-label"><Layers3 size={13} /> LEVEL PROGRESS</span>
          <span className="hud-value font-mono">
            {session.current_level_number} / {session.total_levels}
          </span>
        </div>
      </div>

      {isFinished && (
        <div className="completion-banner">
          <Trophy size={28} />
          <div>
            <h3>INVESTIGATION COMPLETE — CONSPIRACY RESOLVED</h3>
            <p>
              Effective Time: <strong>{formatTime(session.effective_time_seconds)}</strong> (includes {formatTime(session.wrong_penalty_seconds)} wrong answer penalties and {formatTime(session.hint_penalty_seconds)} hint penalties).
            </p>
          </div>
        </div>
      )}

      {/* Main Grid: Left = Dossier & Hints, Right = SQL Terminal & Schema */}
      <div className="workspace-grid">
        {/* Left Column: Dossier */}
        <div className="dossier-column">
          <div className="panel dossier-panel">
            <div className="panel-header">
              <span className="panel-tag">LEVEL {session.current_level_number} OF {session.total_levels}</span>
              <h2>{currentLvl?.title || "Investigation Level"}</h2>
            </div>

            {currentLvl?.narrative_context && (
              <div className="narrative-box">
                <p>{currentLvl.narrative_context}</p>
              </div>
            )}

            <div className="objective-box">
              <div className="objective-header">
                <TargetIcon /> <strong>PRIMARY OBJECTIVE</strong>
              </div>
              <p className="objective-text">{currentLvl?.objective}</p>
            </div>

            {currentLvl?.clue && (
              <div className="clue-box">
                <div className="clue-header">
                  <Lightbulb size={15} /> <strong>FORENSIC LEAD / CLUE</strong>
                </div>
                <p className="clue-text">{currentLvl.clue}</p>
              </div>
            )}

            {/* Tactical Hints */}
            {session.hints && session.hints.length > 0 && (
              <div className="hints-section">
                <div className="hints-header">
                  <HelpCircle size={15} /> <strong>TACTICAL CLUES (+2 MIN PENALTY)</strong>
                </div>
                <div className="hints-list">
                  {session.hints.map((hint) => (
                    <div key={hint.id} className={`hint-card ${hint.unlocked ? "unlocked" : "locked"}`}>
                      <div className="hint-card-top">
                        <span className="hint-title">{hint.title}</span>
                        {hint.unlocked ? (
                          <span className="hint-status-unlocked"><CheckCircle2 size={13} /> Unlocked</span>
                        ) : (
                          <button
                            className="unlock-hint-btn"
                            onClick={() => onPromptHint(hint)}
                            disabled={isFinished}
                          >
                            <LockKeyhole size={12} /> Unlock Hint (+2m)
                          </button>
                        )}
                      </div>
                      {hint.unlocked && hint.body && (
                        <div className="hint-body">
                          <code>{hint.body}</code>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Answer Submission Box */}
          <div className="panel submission-panel">
            <div className="panel-header">
              <span className="panel-tag">FORENSIC VERIFICATION</span>
              <h3>Submit Deduction</h3>
            </div>
            <div className="submission-form">
              <input
                type="text"
                className="input-field answer-input"
                placeholder="Enter exact answer..."
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !answerLoading && !isFinished) {
                    onSubmitAnswer();
                  }
                }}
                disabled={isFinished || session.submission_lock_remaining_seconds > 0}
              />
              <button
                className="primary-button submit-btn"
                onClick={onSubmitAnswer}
                disabled={answerLoading || !answer.trim() || isFinished || session.submission_lock_remaining_seconds > 0}
              >
                {answerLoading ? (
                  <RefreshCw className="spin-icon" size={15} />
                ) : (
                  <>
                    <Send size={15} /> Submit
                  </>
                )}
              </button>
            </div>

            {session.submission_lock_remaining_seconds > 0 && (
              <div className="lock-countdown-alert">
                <AlertTriangle size={15} />
                <span>
                  SUBMISSION LOCKED: Wait <strong>{session.submission_lock_remaining_seconds}s</strong> before next attempt.
                </span>
              </div>
            )}

            {answerMessage && (
              <div className={`answer-alert ${answerMessage.tone}`}>
                {answerMessage.tone === "success" ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
                <span>{answerMessage.text}</span>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: SQL Terminal & Database Schema Explorer */}
        <div className="terminal-column">
          {/* SQL Editor */}
          <div className="panel terminal-panel">
            <div className="terminal-top">
              <div className="terminal-heading">
                <Terminal size={16} />
                <span>SQL INVESTIGATION TERMINAL</span>
                <span className="read-only-badge">READ-ONLY</span>
              </div>
              <div className="terminal-actions">
                <button
                  className="terminal-btn run-btn"
                  onClick={onRunQuery}
                  disabled={queryLoading || !query.trim()}
                  title="Run Query (Ctrl + Enter)"
                >
                  {queryLoading ? (
                    <RefreshCw className="spin-icon" size={14} />
                  ) : (
                    <>
                      <Play size={14} fill="currentColor" /> Run Query
                    </>
                  )}
                </button>
                <button className="terminal-btn clear-btn" onClick={onClearQuery}>
                  Clear
                </button>
              </div>
            </div>

            <div className="editor-wrapper">
              <textarea
                className="sql-editor"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => {
                  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
                    e.preventDefault();
                    if (!queryLoading && query.trim()) {
                      onRunQuery();
                    }
                  }
                }}
                placeholder="Enter read-only SQL query here..."
                rows={5}
                spellCheck={false}
              />
            </div>

            {workspaceError && (
              <div className="query-error-alert">
                <AlertCircle size={16} />
                <span>{workspaceError}</span>
              </div>
            )}

            {/* Results Grid */}
            <div className="query-results-area">
              {queryResult ? (
                <div className="results-container">
                  <div className="results-meta">
                    <span>
                      Returned <strong>{queryResult.row_count}</strong> rows in{" "}
                      <strong>{formatMs(queryResult.duration_ms)}</strong> (capped at {queryResult.max_rows})
                    </span>
                  </div>
                  <div className="table-scroll-wrapper">
                    <table className="result-data-table">
                      <thead>
                        <tr>
                          {queryResult.columns.map((col, idx) => (
                            <th key={idx}>{col}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {queryResult.rows.length === 0 ? (
                          <tr>
                            <td colSpan={queryResult.columns.length} className="empty-row">
                              0 rows returned.
                            </td>
                          </tr>
                        ) : (
                          queryResult.rows.map((row, rIdx) => (
                            <tr key={rIdx}>
                              {row.map((val, cIdx) => (
                                <td key={cIdx} className="font-mono">
                                  {val === null ? <span className="null-val">NULL</span> : String(val)}
                                </td>
                              ))}
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div className="terminal-placeholder">
                  <Database size={24} />
                  <p>Execute a SQL SELECT statement above to inspect investigation evidence.</p>
                </div>
              )}
            </div>
          </div>

          {/* Relational Schema Explorer */}
          <div className="panel schema-panel">
            <div className="panel-header">
              <div className="schema-header-left">
                <Database size={16} />
                <h3>UNLOCKED RELATIONAL EVIDENCE TABLES</h3>
              </div>
              {lockedTableCount > 0 && (
                <span className="locked-counter-badge">
                  <LockKeyhole size={12} /> {lockedTableCount} Tables Locked
                </span>
              )}
            </div>

            <div className="schema-tables-grid">
              {tables.map((table) => (
                <div key={table.name} className="schema-table-card">
                  <div className="table-card-top">
                    <button
                      className="table-card-name"
                      onClick={() => onSelectTable(table.name)}
                      title={`Preview ${table.name}`}
                    >
                      <code>{table.name}</code>
                      <ExternalLink size={12} />
                    </button>
                    <span className="table-label">{table.label}</span>
                  </div>
                  {table.description && <p className="table-desc">{table.description}</p>}
                  <div className="columns-chip-list">
                    {table.columns.map((col) => (
                      <span
                        key={col.name}
                        className={`col-chip ${col.is_primary_key ? "pk" : ""}`}
                        title={`${col.name} (${col.data_type}) ${col.is_primary_key ? " [PRIMARY KEY]" : ""}`}
                      >
                        {col.is_primary_key && <KeyRound size={10} />}
                        <strong>{col.name}</strong>
                        <small>{col.data_type}</small>
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function TargetIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <circle cx="12" cy="12" r="6" />
      <circle cx="12" cy="12" r="2" />
    </svg>
  );
}

function QuizScreen({
  questions,
  answers,
  setAnswers,
  result,
  session,
  participant,
  onSubmit,
  onProceed,
  onBack,
}: {
  questions: QuizQuestion[];
  answers: Record<string, string>;
  setAnswers: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  result: { score: number; total: number; qualified: boolean } | null;
  session: GameState | null;
  participant: Participant | null;
  onSubmit: () => void;
  onProceed: () => void;
  onBack: () => void;
}) {
  const answeredCount = Object.keys(answers).length;

  return (
    <div className="quiz-page page-wrap">
      <div className="quiz-container panel">
        <div className="panel-header">
          <span className="panel-tag">PRELIMINARY ROUND</span>
          <h2>DBMS &amp; SQL Qualifier Quiz</h2>
          <p className="quiz-lead">
            Answer the following foundational SQL questions. Score at least <strong>3/5</strong> to qualify for the live investigation.
          </p>
        </div>

        {participant && (
          <div className="quiz-participant-info">
            <UserIcon size={14} />
            <span>Detective: <strong>{participant.display_name || participant.email}</strong></span>
          </div>
        )}

        {result && (
          <div className={`quiz-result-banner ${result.qualified ? "qualified" : "disqualified"}`}>
            {result.qualified ? <CheckCircle2 size={24} /> : <AlertTriangle size={24} />}
            <div>
              <h4>{result.qualified ? "QUALIFIED FOR INVENTE 2026 INVESTIGATION!" : "QUALIFICATION SCORE NOT MET"}</h4>
              <p>
                You scored <strong>{result.score} / {result.total}</strong>.
                {result.qualified
                  ? " You may now proceed into the main investigation."
                  : " Review SQL fundamentals and try again."}
              </p>
            </div>
            {result.qualified && (
              <button className="primary-button" onClick={onProceed}>
                Enter Case <ArrowRight size={15} />
              </button>
            )}
          </div>
        )}

        <div className="questions-list">
          {questions.map((q, qIndex) => (
            <div key={q.id} className="question-card">
              <div className="question-prompt">
                <span className="q-number">Q{qIndex + 1}.</span>
                <span>{q.prompt}</span>
              </div>
              <div className="options-list">
                {q.options.map((opt) => {
                  const selected = answers[q.id] === opt.id;
                  return (
                    <label
                      key={opt.id}
                      className={`option-label ${selected ? "selected" : ""}`}
                    >
                      <input
                        type="radio"
                        name={q.id}
                        value={opt.id}
                        checked={selected}
                        onChange={() => setAnswers((prev) => ({ ...prev, [q.id]: opt.id }))}
                      />
                      <span>{opt.option_text}</span>
                    </label>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        <div className="quiz-actions">
          <button className="secondary-button" onClick={onBack}>
            Back
          </button>
          <button
            className="primary-button"
            onClick={onSubmit}
            disabled={answeredCount < questions.length}
          >
            Submit Quiz ({answeredCount}/{questions.length})
          </button>
        </div>
      </div>
    </div>
  );
}

function Leaderboard({
  entries,
  onBack,
}: {
  entries: LeaderboardEntry[];
  onBack: () => void;
}) {
  return (
    <div className="leaderboard-page page-wrap">
      <div className="panel">
        <div className="panel-header">
          <span className="panel-tag">LIVE STANDINGS</span>
          <h2>Invente 2026 Investigation Leaderboard</h2>
          <p>Rankings sorted by completed levels and effective time (duration + wrong answer penalties + hint penalties).</p>
        </div>

        <div className="table-scroll-wrapper">
          <table className="leaderboard-table">
            <thead>
              <tr>
                <th>RANK</th>
                <th>SQUAD / DETECTIVE</th>
                <th>CURRENT LEVEL</th>
                <th>PROGRESS</th>
                <th>EFFECTIVE TIME</th>
                <th>STATUS</th>
              </tr>
            </thead>
            <tbody>
              {entries.length === 0 ? (
                <tr>
                  <td colSpan={6} className="empty-row">
                    No active sessions recorded yet.
                  </td>
                </tr>
              ) : (
                entries.map((entry) => (
                  <tr key={entry.team_name} className={entry.rank <= 3 ? `top-${entry.rank}` : ""}>
                    <td className="rank-col">
                      {entry.rank === 1 ? "🥇 1" : entry.rank === 2 ? "🥈 2" : entry.rank === 3 ? "🥉 3" : entry.rank}
                    </td>
                    <td className="team-col">
                      <strong>{entry.team_name}</strong>
                    </td>
                    <td className="font-mono">Level {entry.current_level}</td>
                    <td>
                      <div className="progress-bar-wrap">
                        <div className="progress-bar-fill" style={{ width: `${entry.progress_percent}%` }} />
                        <span className="progress-text">{entry.progress_percent}%</span>
                      </div>
                    </td>
                    <td className="font-mono">{formatTime(entry.effective_time_seconds)}</td>
                    <td>
                      <span className={`status-badge ${entry.status.toLowerCase()}`}>
                        {entry.status}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="leaderboard-footer">
          <button className="secondary-button" onClick={onBack}>
            Back
          </button>
        </div>
      </div>
    </div>
  );
}

function Organizer({
  data,
  onBack,
}: {
  data: any;
  onBack: () => void;
}) {
  return (
    <div className="organizer-page page-wrap">
      <div className="panel">
        <div className="panel-header">
          <span className="panel-tag">EVENT TELEMETRY</span>
          <h2>Organizer Telemetry Console</h2>
          <p>Real-time game metrics and scoring parameters.</p>
        </div>

        {data ? (
          <div className="telemetry-grid">
            <div className="stat-card">
              <span className="stat-label">Total Sessions</span>
              <span className="stat-number font-mono">{data.total_sessions}</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Active Investigating</span>
              <span className="stat-number font-mono text-amber">{data.active_sessions}</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Solved &amp; Completed</span>
              <span className="stat-number font-mono highlight">{data.completed_sessions}</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Investigation Levels</span>
              <span className="stat-number font-mono">{data.total_levels}</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Evidence Tables</span>
              <span className="stat-number font-mono">{data.total_tables}</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Wrong Answer Penalty</span>
              <span className="stat-number font-mono">+{data.wrong_penalty_minutes} min</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Tactical Hint Penalty</span>
              <span className="stat-number font-mono">+{data.hint_penalty_minutes} min</span>
            </div>
          </div>
        ) : (
          <p>Loading telemetry...</p>
        )}

        <div className="leaderboard-footer">
          <button className="secondary-button" onClick={onBack}>
            Back
          </button>
        </div>
      </div>
    </div>
  );
}

function DisclaimerModal({ onClose }: { onClose: () => void }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-top">
          <ShieldAlert size={22} className="text-amber" />
          <h3>Canon Disclaimer</h3>
          <button className="close-btn" onClick={onClose} aria-label="Close modal">
            <X size={18} />
          </button>
        </div>
        <div className="modal-body">
          <p className="disclaimer-statement">{DISCLAIMER_TEXT}</p>
          <p>
            All characters, events, timelines, references, and scenarios featured in this case
            are purely fictional creations prepared specifically for the Invente 2026 SQL investigation challenge.
          </p>
        </div>
        <div className="modal-actions">
          <button className="primary-button" onClick={onClose}>
            Acknowledge &amp; Dismiss
          </button>
        </div>
      </div>
    </div>
  );
}

function HintConfirmModal({
  hint,
  loading,
  onConfirm,
  onClose,
}: {
  hint: HintItem;
  loading: boolean;
  onConfirm: () => void;
  onClose: () => void;
}) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-top">
          <Lightbulb size={22} className="text-amber" />
          <h3>Unlock Tactical Clue?</h3>
          <button className="close-btn" onClick={onClose} aria-label="Close modal">
            <X size={18} />
          </button>
        </div>
        <div className="modal-body">
          <p>
            Are you sure you want to unlock clue <strong>"{hint.title}"</strong>?
          </p>
          <div className="penalty-warning-box">
            <AlertTriangle size={18} />
            <span>
              Unlocking this hint will immediately add <strong>+{hint.penalty_minutes} minutes</strong> to your team's effective competition time.
            </span>
          </div>
        </div>
        <div className="modal-actions">
          <button className="secondary-button" onClick={onClose} disabled={loading}>
            Cancel
          </button>
          <button className="primary-button danger" onClick={onConfirm} disabled={loading}>
            {loading ? <RefreshCw className="spin-icon" size={15} /> : "Unlock & Accept +2m Penalty"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;