import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import axios from "axios";
import { API, useAuth } from "../App";
import { toast } from "sonner";
import { Rocket, House, FolderOpen, Users, Bell, User, SignOut, Plus, Lightning, MagnifyingGlass, ArrowsClockwise, Sparkle, TrendingUp } from "@phosphor-icons/react";

const domainColors = { engineering: "#3B82F6", design: "#EC4899", business: "#10B981" };
const stageStyles = { ideation: "stage-ideation", mvp: "stage-mvp", validation: "stage-validation", scaling: "stage-scaling" };

function ScoreRing({ score, size = 60 }) {
  const radius = (size - 8) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 100) * circumference;
  const color = score < 40 ? "#EF4444" : score < 70 ? "#F59E0B" : "#10B981";
  return (
    <div className="score-ring" style={{ width: size, height: size }}>
      <svg width={size} height={size}>
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="#141428" strokeWidth="4" />
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke={color} strokeWidth="4" strokeDasharray={circumference} strokeDashoffset={circumference - progress} strokeLinecap="round" />
      </svg>
      <div className="score-value">{Math.round(score)}%</div>
    </div>
  );
}

function MomentumBar({ score }) {
  const color = score < 40 ? "momentum-low" : score < 70 ? "momentum-medium" : "momentum-high";
  return (
    <div className="w-full h-2 bg-[#141428] rounded-full overflow-hidden">
      <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${score}%` }}></div>
    </div>
  );
}

function MatchCard({ match, onClick }) {
  const project = match.project;
  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} whileHover={{ y: -4 }} className="glow-card rounded-2xl p-6 cursor-pointer" onClick={onClick}>
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className={`px-2 py-1 rounded-md text-xs font-medium ${stageStyles[project.stage]}`}>{project.stage}</span>
            {project.industry_vertical && <span className="text-xs text-[#94A3B8] bg-white/5 px-2 py-1 rounded-md">{project.industry_vertical}</span>}
          </div>
          <h3 className="font-semibold text-lg mb-1">{project.title}</h3>
          <p className="text-sm text-[#94A3B8] line-clamp-2">{project.description}</p>
        </div>
        <ScoreRing score={match.match_score} />
      </div>
      <div className="flex flex-wrap gap-2 mb-4">
        {project.required_skills?.slice(0, 4).map((skill, i) => (
          <span key={i} className="text-xs px-2 py-1 rounded-full bg-[#6C63FF]/20 text-[#A5A0FF]">{skill.skill_name}</span>
        ))}
      </div>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2"><Users size={16} className="text-[#94A3B8]" /><span className="text-sm text-[#94A3B8]">{match.team_size} / {match.max_team_size}</span></div>
        <div className="flex-1 mx-4"><MomentumBar score={project.momentum_score || 0} /></div>
        {match.used_ai && <span className="ai-badge">✦ AI</span>}
      </div>
    </motion.div>
  );
}

function Sidebar({ onLogout }) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const navItems = [
    { icon: House, label: "Discover", path: "/dashboard" },
    { icon: FolderOpen, label: "My Projects", path: "/projects?mine=true" },
    { icon: Bell, label: "Invitations", path: "/invitations" },
    { icon: User, label: "Profile", path: "/profile" },
  ];
  return (
    <aside className="w-64 border-r border-white/10 min-h-screen p-6 flex flex-col">
      <Link to="/" className="flex items-center gap-3 mb-10">
        <div className="w-10 h-10 bg-gradient-to-br from-[#6C63FF] to-[#EC4899] rounded-xl flex items-center justify-center">
          <Rocket weight="fill" className="w-5 h-5 text-white" />
        </div>
        <span className="font-bold text-xl">Antigravity</span>
      </Link>
      <nav className="flex-1 space-y-2">
        {navItems.map((item) => (
          <Link key={item.path} to={item.path} className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-[#141428] transition-colors text-[#94A3B8] hover:text-white">
            <item.icon size={20} />
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>
      <div className="border-t border-white/10 pt-4 mt-4">
        <div className="flex items-center gap-3 px-4 py-3">
          <div className="w-10 h-10 rounded-full flex items-center justify-center text-white font-semibold" style={{ background: domainColors[user?.domain] || "#6C63FF" }}>
            {user?.full_name?.charAt(0) || "U"}
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-medium truncate">{user?.full_name}</div>
            <div className="text-xs text-[#94A3B8] capitalize">{user?.domain}</div>
          </div>
        </div>
        <button onClick={onLogout} className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-red-500/10 transition-colors text-[#94A3B8] hover:text-red-400 w-full">
          <SignOut size={20} />
          <span>Sign out</span>
        </button>
      </div>
    </aside>
  );
}

export default function Dashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    if (user && !user.onboarding_complete) {
      navigate("/onboarding");
      return;
    }
    fetchMatches();
  }, [user]);

  const fetchMatches = async () => {
    try {
      const { data } = await axios.get(`${API}/match/projects`, { withCredentials: true });
      setMatches(data);
    } catch (e) {
      console.error("Failed to fetch matches", e);
    } finally {
      setLoading(false);
    }
  };

  const refreshMatches = async () => {
    setRefreshing(true);
    await fetchMatches();
    setRefreshing(false);
    toast.success("Matches refreshed!");
  };

  const handleLogout = async () => {
    await logout();
    navigate("/");
  };

  return (
    <div className="min-h-screen bg-[#0D0D1A] flex">
      <Sidebar onLogout={handleLogout} />
      <main className="flex-1 p-8">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h1 className="text-3xl font-bold mb-2">Your Matches</h1>
              <p className="text-[#94A3B8]">Projects that match your skills and interests</p>
            </div>
            <div className="flex items-center gap-4">
              <button onClick={refreshMatches} disabled={refreshing} className="btn-secondary flex items-center gap-2" data-testid="refresh-matches-btn">
                <ArrowsClockwise size={18} className={refreshing ? "animate-spin" : ""} /> Refresh
              </button>
              <Link to="/projects/new" className="btn-primary flex items-center gap-2" data-testid="create-project-btn">
                <Plus weight="bold" size={18} /> New Project
              </Link>
            </div>
          </div>
          {loading ? (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div key={i} className="glow-card rounded-2xl p-6 animate-pulse">
                  <div className="h-6 w-24 bg-white/5 rounded mb-4"></div>
                  <div className="h-4 w-full bg-white/5 rounded mb-2"></div>
                  <div className="h-4 w-2/3 bg-white/5 rounded mb-4"></div>
                  <div className="flex gap-2 mb-4">
                    <div className="h-6 w-16 bg-white/5 rounded-full"></div>
                    <div className="h-6 w-16 bg-white/5 rounded-full"></div>
                  </div>
                  <div className="h-2 w-full bg-white/5 rounded"></div>
                </div>
              ))}
            </div>
          ) : matches.length === 0 ? (
            <div className="text-center py-20">
              <Lightning weight="duotone" size={64} className="text-[#6C63FF] mx-auto mb-4" />
              <h2 className="text-xl font-semibold mb-2">No matches yet</h2>
              <p className="text-[#94A3B8] mb-6">Add more skills to your profile or create a project to find matches</p>
              <div className="flex items-center justify-center gap-4">
                <Link to="/profile" className="btn-secondary">Update Skills</Link>
                <Link to="/projects/new" className="btn-primary">Create Project</Link>
              </div>
            </div>
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {matches.map((match, i) => (
                <MatchCard key={match.project.id} match={match} onClick={() => navigate(`/projects/${match.project.id}`)} />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
