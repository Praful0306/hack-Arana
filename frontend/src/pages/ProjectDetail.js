import { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import axios from "axios";
import { API, useAuth, formatApiErrorDetail } from "../App";
import { toast } from "sonner";
import { ArrowLeft, Users, Target, Lightning, Robot, MapTrifold, Plus, CheckCircle, Clock, Warning, CaretRight, Sparkle, ChatCircle } from "@phosphor-icons/react";
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, ResponsiveContainer } from "recharts";

const domainColors = { engineering: "#3B82F6", design: "#EC4899", business: "#10B981" };
const stageStyles = { ideation: "stage-ideation", mvp: "stage-mvp", validation: "stage-validation", scaling: "stage-scaling" };
const statusColors = { pending: "#94A3B8", active: "#3B82F6", review: "#F59E0B", completed: "#10B981", blocked: "#EF4444" };

function TabButton({ active, onClick, children, icon: Icon }) {
  return (
    <button onClick={onClick} className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-all ${active ? "border-[#6C63FF] text-white" : "border-transparent text-[#94A3B8] hover:text-white"}`}>
      {Icon && <Icon size={18} />} {children}
    </button>
  );
}

function SkillCoverageBar({ skills }) {
  const covered = skills.filter((s) => s.is_covered).length;
  const total = skills.length || 1;
  const pct = (covered / total) * 100;
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-sm"><span>Skill Coverage</span><span className="font-mono font-bold">{Math.round(pct)}%</span></div>
      <div className="w-full h-3 bg-[#141428] rounded-full overflow-hidden"><div className="h-full bg-gradient-to-r from-[#6C63FF] to-[#10B981] rounded-full" style={{ width: `${pct}%` }}></div></div>
      <div className="flex flex-wrap gap-2">
        {skills.map((s, i) => <span key={i} className={`text-xs px-3 py-1 rounded-full ${s.is_covered ? "bg-[#10B981]/20 text-[#10B981]" : "bg-red-500/20 text-red-400"}`}>{s.skill_name}</span>)}
      </div>
    </div>
  );
}

function MilestoneCard({ milestone, onStatusChange }) {
  const color = statusColors[milestone.status] || "#94A3B8";
  return (
    <div className="kanban-card">
      <div className="flex items-start justify-between mb-2">
        <h4 className="font-medium">{milestone.title}</h4>
        {milestone.owner_domain && <span className="text-xs px-2 py-1 rounded" style={{ background: `${domainColors[milestone.owner_domain]}20`, color: domainColors[milestone.owner_domain] }}>{milestone.owner_domain}</span>}
      </div>
      {milestone.description && <p className="text-xs text-[#94A3B8] mb-3">{milestone.description}</p>}
      {milestone.due_date && <div className="text-xs text-[#94A3B8] flex items-center gap-1"><Clock size={12} /> Due: {new Date(milestone.due_date).toLocaleDateString()}</div>}
      <select value={milestone.status} onChange={(e) => onStatusChange(milestone.id, e.target.value)} className="mt-3 w-full text-xs px-2 py-1 rounded bg-[#0D0D1A] border border-white/10">
        <option value="pending">Pending</option>
        <option value="active">Active</option>
        <option value="review">Review</option>
        <option value="completed">Completed</option>
        <option value="blocked">Blocked</option>
      </select>
    </div>
  );
}

export default function ProjectDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [project, setProject] = useState(null);
  const [team, setTeam] = useState(null);
  const [milestones, setMilestones] = useState([]);
  const [skillGaps, setSkillGaps] = useState(null);
  const [readiness, setReadiness] = useState(null);
  const [roadmap, setRoadmap] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("overview");
  const [generatingRoadmap, setGeneratingRoadmap] = useState(false);
  const [newMilestone, setNewMilestone] = useState({ title: "", description: "", owner_domain: "" });
  const [showMilestoneForm, setShowMilestoneForm] = useState(false);

  useEffect(() => { fetchProject(); }, [id]);

  const fetchProject = async () => {
    try {
      const [projRes, teamRes, msRes, gapsRes, readyRes] = await Promise.all([
        axios.get(`${API}/projects/${id}`, { withCredentials: true }),
        axios.get(`${API}/teams/${id}`, { withCredentials: true }).catch(() => ({ data: null })),
        axios.get(`${API}/projects/${id}/milestones`, { withCredentials: true }),
        axios.get(`${API}/ai/skill-gaps/${id}`, { withCredentials: true }),
        axios.get(`${API}/ai/readiness/${id}`, { withCredentials: true }),
      ]);
      setProject(projRes.data);
      setTeam(teamRes.data);
      setMilestones(msRes.data);
      setSkillGaps(gapsRes.data);
      setReadiness(readyRes.data);
    } catch (e) { console.error(e); toast.error("Failed to load project"); } finally { setLoading(false); }
  };

  const generateRoadmap = async () => {
    setGeneratingRoadmap(true);
    try {
      const { data } = await axios.post(`${API}/ai/roadmap/${id}`, {}, { withCredentials: true });
      setRoadmap(data.roadmap);
      toast.success("Roadmap generated!");
    } catch (e) { toast.error("Failed to generate roadmap"); } finally { setGeneratingRoadmap(false); }
  };

  const createMilestone = async () => {
    if (!newMilestone.title) { toast.error("Title required"); return; }
    try {
      const { data } = await axios.post(`${API}/projects/${id}/milestones`, newMilestone, { withCredentials: true });
      setMilestones([...milestones, data]);
      setNewMilestone({ title: "", description: "", owner_domain: "" });
      setShowMilestoneForm(false);
      toast.success("Milestone added!");
    } catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); }
  };

  const updateMilestoneStatus = async (milestoneId, status) => {
    try {
      await axios.patch(`${API}/projects/${id}/milestones/${milestoneId}`, { status }, { withCredentials: true });
      setMilestones(milestones.map((m) => m.id === milestoneId ? { ...m, status } : m));
      if (status === "completed") toast.success("Milestone completed!");
    } catch (e) { toast.error("Failed to update"); }
  };

  if (loading) return <div className="min-h-screen bg-[#0D0D1A] flex items-center justify-center"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#6C63FF]"></div></div>;
  if (!project) return <div className="min-h-screen bg-[#0D0D1A] flex items-center justify-center text-[#94A3B8]">Project not found</div>;

  const radarData = readiness ? [
    { subject: "Problem", value: readiness.dimensions.problem_clarity },
    { subject: "Market", value: readiness.dimensions.market_size },
    { subject: "Solution", value: readiness.dimensions.solution_viability },
    { subject: "Team", value: readiness.dimensions.team_completeness },
    { subject: "Execution", value: readiness.dimensions.execution_evidence },
  ] : [];

  const milestonesByStatus = { pending: milestones.filter((m) => m.status === "pending"), active: milestones.filter((m) => m.status === "active"), review: milestones.filter((m) => m.status === "review"), completed: milestones.filter((m) => m.status === "completed"), blocked: milestones.filter((m) => m.status === "blocked") };

  return (
    <div className="min-h-screen bg-[#0D0D1A]">
      <header className="glass sticky top-0 z-50 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/dashboard" className="text-[#94A3B8] hover:text-white"><ArrowLeft size={24} /></Link>
            <div>
              <div className="flex items-center gap-3"><h1 className="text-xl font-bold">{project.title}</h1><span className={`px-2 py-1 rounded text-xs font-medium ${stageStyles[project.stage]}`}>{project.stage}</span></div>
              <p className="text-sm text-[#94A3B8]">by {project.founder_name}</p>
            </div>
          </div>
          <Link to={`/projects/${id}/chat`} className="btn-primary flex items-center gap-2" data-testid="open-ai-chat-btn"><ChatCircle weight="fill" size={18} /> AI Co-Founder</Link>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 py-4">
        <div className="flex gap-2 border-b border-white/10 mb-6">
          <TabButton active={activeTab === "overview"} onClick={() => setActiveTab("overview")} icon={Target}>Overview</TabButton>
          <TabButton active={activeTab === "team"} onClick={() => setActiveTab("team")} icon={Users}>Team</TabButton>
          <TabButton active={activeTab === "milestones"} onClick={() => setActiveTab("milestones")} icon={CheckCircle}>Milestones</TabButton>
          <TabButton active={activeTab === "ai"} onClick={() => setActiveTab("ai")} icon={Robot}>AI Tools</TabButton>
          <TabButton active={activeTab === "roadmap"} onClick={() => setActiveTab("roadmap")} icon={MapTrifold}>Roadmap</TabButton>
        </div>

        {activeTab === "overview" && (
          <div className="grid lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <div className="glow-card rounded-2xl p-6">
                <h3 className="font-semibold mb-4">About</h3>
                <p className="text-[#94A3B8] mb-4">{project.description}</p>
                {project.problem_statement && <div className="mb-4"><div className="text-sm font-medium mb-1">Problem</div><p className="text-sm text-[#94A3B8]">{project.problem_statement}</p></div>}
                {project.target_market && <div><div className="text-sm font-medium mb-1">Target Market</div><p className="text-sm text-[#94A3B8]">{project.target_market}</p></div>}
              </div>
              {skillGaps && <div className="glow-card rounded-2xl p-6"><h3 className="font-semibold mb-4">Skill Coverage</h3><SkillCoverageBar skills={skillGaps.skills} /></div>}
            </div>
            <div className="space-y-6">
              {readiness && (
                <div className="glow-card rounded-2xl p-6">
                  <div className="flex items-center justify-between mb-4"><h3 className="font-semibold">Readiness</h3><span className="ai-badge">✦ AI</span></div>
                  <div className="text-center mb-4"><div className="text-4xl font-bold font-mono">{Math.round(readiness.overall_score)}</div><div className="text-sm text-[#94A3B8]">Overall Score</div></div>
                  <div className="h-48"><ResponsiveContainer width="100%" height="100%"><RadarChart data={radarData}><PolarGrid stroke="#ffffff20" /><PolarAngleAxis dataKey="subject" tick={{ fill: "#94A3B8", fontSize: 11 }} /><Radar dataKey="value" stroke="#6C63FF" fill="#6C63FF" fillOpacity={0.3} /></RadarChart></ResponsiveContainer></div>
                  {readiness.next_actions?.length > 0 && <div className="mt-4"><div className="text-sm font-medium mb-2">Next Actions</div>{readiness.next_actions.map((a, i) => <div key={i} className="text-xs text-[#94A3B8] flex items-start gap-2 mb-1"><CaretRight size={12} className="mt-0.5 text-[#6C63FF]" /> {a}</div>)}</div>}
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === "team" && (
          <div className="space-y-6">
            <div className="glow-card rounded-2xl p-6">
              <div className="flex items-center justify-between mb-6"><h3 className="font-semibold">Team Members</h3><span className="text-sm text-[#94A3B8]">{team?.members?.length || 0} / {project.max_team_size}</span></div>
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {team?.members?.map((m, i) => (
                  <div key={i} className="p-4 bg-[#0D0D1A] rounded-xl border border-white/10">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 rounded-full flex items-center justify-center text-white font-semibold" style={{ background: domainColors[m.domain] }}>{m.name?.charAt(0)}</div>
                      <div><div className="font-medium">{m.name}</div><div className="text-xs text-[#94A3B8] capitalize">{m.domain} • {m.role}</div></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            {team && (
              <div className="grid md:grid-cols-2 gap-6">
                <div className="glow-card rounded-2xl p-6"><div className="text-sm text-[#94A3B8] mb-2">Health Score</div><div className="text-3xl font-bold font-mono">{Math.round(team.health_score || 50)}</div><div className="w-full h-2 bg-[#141428] rounded-full mt-2"><div className="h-full bg-[#10B981] rounded-full" style={{ width: `${team.health_score || 50}%` }}></div></div></div>
                <div className="glow-card rounded-2xl p-6"><div className="text-sm text-[#94A3B8] mb-2">Diversity Score</div><div className="text-3xl font-bold font-mono">{Math.round(team.diversity_score || 33)}</div><div className="w-full h-2 bg-[#141428] rounded-full mt-2"><div className="h-full bg-[#6C63FF] rounded-full" style={{ width: `${team.diversity_score || 33}%` }}></div></div></div>
              </div>
            )}
          </div>
        )}

        {activeTab === "milestones" && (
          <div>
            <div className="flex items-center justify-between mb-6">
              <h3 className="font-semibold">Milestones</h3>
              <button onClick={() => setShowMilestoneForm(true)} className="btn-primary flex items-center gap-2" data-testid="add-milestone-btn"><Plus weight="bold" size={16} /> Add Milestone</button>
            </div>
            {showMilestoneForm && (
              <div className="glow-card rounded-2xl p-6 mb-6">
                <h4 className="font-medium mb-4">New Milestone</h4>
                <div className="grid md:grid-cols-3 gap-4 mb-4">
                  <input type="text" value={newMilestone.title} onChange={(e) => setNewMilestone({ ...newMilestone, title: e.target.value })} placeholder="Title" className="px-4 py-2 rounded-xl" data-testid="milestone-title-input" />
                  <input type="text" value={newMilestone.description} onChange={(e) => setNewMilestone({ ...newMilestone, description: e.target.value })} placeholder="Description" className="px-4 py-2 rounded-xl" />
                  <select value={newMilestone.owner_domain} onChange={(e) => setNewMilestone({ ...newMilestone, owner_domain: e.target.value })} className="px-4 py-2 rounded-xl"><option value="">Owner Domain</option><option value="engineering">Engineering</option><option value="design">Design</option><option value="business">Business</option></select>
                </div>
                <div className="flex gap-2"><button onClick={createMilestone} className="btn-primary" data-testid="save-milestone-btn">Save</button><button onClick={() => setShowMilestoneForm(false)} className="btn-secondary">Cancel</button></div>
              </div>
            )}
            <div className="grid grid-cols-5 gap-4">
              {["pending", "active", "review", "completed", "blocked"].map((status) => (
                <div key={status} className="kanban-column">
                  <div className="flex items-center gap-2 mb-4"><div className="w-3 h-3 rounded-full" style={{ background: statusColors[status] }}></div><span className="text-sm font-medium capitalize">{status}</span><span className="text-xs text-[#94A3B8]">({milestonesByStatus[status]?.length || 0})</span></div>
                  {milestonesByStatus[status]?.map((m) => <MilestoneCard key={m.id} milestone={m} onStatusChange={updateMilestoneStatus} />)}
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === "ai" && (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div className="glow-card rounded-2xl p-6"><div className="flex items-center justify-between mb-4"><h3 className="font-semibold">AI Co-Founder</h3><span className="ai-badge">✦ AI</span></div><p className="text-sm text-[#94A3B8] mb-4">Chat with an AI advisor that knows your project.</p><Link to={`/projects/${id}/chat`} className="btn-primary w-full flex items-center justify-center gap-2"><ChatCircle weight="fill" size={18} /> Start Chat</Link></div>
            <div className="glow-card rounded-2xl p-6"><div className="flex items-center justify-between mb-4"><h3 className="font-semibold">Skill Gap Analysis</h3><span className="ai-badge">✦ AI</span></div><p className="text-sm text-[#94A3B8] mb-4">See which skills your team is missing.</p>{skillGaps && <div className="text-2xl font-bold font-mono text-center">{Math.round(skillGaps.coverage_percentage)}%<div className="text-xs text-[#94A3B8] font-normal">Coverage</div></div>}</div>
            <div className="glow-card rounded-2xl p-6"><div className="flex items-center justify-between mb-4"><h3 className="font-semibold">Readiness Score</h3><span className="ai-badge">✦ AI</span></div><p className="text-sm text-[#94A3B8] mb-4">How ready is your startup to launch?</p>{readiness && <div className="text-2xl font-bold font-mono text-center">{Math.round(readiness.overall_score)}<div className="text-xs text-[#94A3B8] font-normal">Overall</div></div>}</div>
          </div>
        )}

        {activeTab === "roadmap" && (
          <div>
            <div className="flex items-center justify-between mb-6">
              <div><h3 className="font-semibold">Smart Roadmap</h3><p className="text-sm text-[#94A3B8]">AI-generated 6-week sprint plan</p></div>
              <button onClick={generateRoadmap} disabled={generatingRoadmap} className="btn-primary flex items-center gap-2" data-testid="generate-roadmap-btn">{generatingRoadmap ? <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div> : <><Sparkle weight="fill" /> Generate Roadmap</>}</button>
            </div>
            {roadmap ? (
              <div className="space-y-6">
                {roadmap.bandwidth_warning && <div className="bg-amber-500/10 border border-amber-500/30 text-amber-400 px-4 py-3 rounded-xl flex items-center gap-2"><Warning size={18} /> {roadmap.bandwidth_warning}</div>}
                {roadmap.missing_role_alert && <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-xl flex items-center gap-2"><Warning size={18} /> {roadmap.missing_role_alert}</div>}
                <div className="grid md:grid-cols-3 gap-6">
                  {roadmap.sprints?.map((sprint) => (
                    <div key={sprint.sprint_number} className="glow-card rounded-2xl p-6">
                      <div className="flex items-center justify-between mb-3"><span className="text-xs text-[#6C63FF] font-medium">{sprint.week_range}</span><span className="text-xs bg-[#6C63FF]/20 text-[#A5A0FF] px-2 py-1 rounded">Sprint {sprint.sprint_number}</span></div>
                      <h4 className="font-semibold mb-2">{sprint.title}</h4>
                      <p className="text-sm text-[#94A3B8] italic mb-4">"{sprint.goal}"</p>
                      <div className="space-y-2">
                        {sprint.milestones?.map((m, i) => (
                          <div key={i} className="p-3 bg-[#0D0D1A] rounded-lg border border-white/5">
                            <div className="flex items-start justify-between"><span className="text-sm font-medium">{m.title}</span>{m.is_critical_path && <span className="text-xs text-[#6C63FF]">Critical</span>}</div>
                            <div className="flex items-center gap-2 mt-2"><span className="text-xs px-2 py-0.5 rounded" style={{ background: `${domainColors[m.owner_domain]}20`, color: domainColors[m.owner_domain] }}>{m.owner_domain}</span><span className="text-xs text-[#94A3B8]">{m.estimated_hours}h</span></div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
                {roadmap.definition_of_done && <div className="bg-[#141428] rounded-xl p-4 border-l-4 border-[#10B981]"><div className="text-sm font-medium mb-1 text-[#10B981]">Definition of Done (Week 6)</div><p className="text-sm text-[#94A3B8]">{roadmap.definition_of_done}</p></div>}
              </div>
            ) : (
              <div className="text-center py-20 text-[#94A3B8]"><MapTrifold size={64} className="mx-auto mb-4 opacity-50" /><p>No roadmap generated yet. Click the button above to create one.</p></div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
