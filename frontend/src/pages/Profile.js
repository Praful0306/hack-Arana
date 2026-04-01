import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import axios from "axios";
import { API, useAuth, formatApiErrorDetail } from "../App";
import { toast } from "sonner";
import { ArrowLeft, User, Star, Code, Palette, ChartLineUp, PencilSimple, GraduationCap, Clock, Scales, LinkedinLogo, GithubLogo, Globe } from "@phosphor-icons/react";

const domainColors = { engineering: "#3B82F6", design: "#EC4899", business: "#10B981" };
const domainIcons = { engineering: Code, design: Palette, business: ChartLineUp };

export default function Profile() {
  const { user, logout, refreshUser } = useAuth();
  const navigate = useNavigate();
  const [editing, setEditing] = useState(false);
  const [myProjects, setMyProjects] = useState([]);
  const [loading, setLoading] = useState(true);

  const [bio, setBio] = useState("");
  const [institution, setInstitution] = useState("");
  const [yearOfStudy, setYearOfStudy] = useState(2);
  const [availabilityHours, setAvailabilityHours] = useState(10);
  const [riskTolerance, setRiskTolerance] = useState(5);
  const [githubUrl, setGithubUrl] = useState("");
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [portfolioUrl, setPortfolioUrl] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (user) {
      setBio(user.profile?.bio || "");
      setInstitution(user.profile?.institution || "");
      setYearOfStudy(user.profile?.year_of_study || 2);
      setAvailabilityHours(user.profile?.availability_hours || 10);
      setRiskTolerance(user.profile?.risk_tolerance || 5);
      setGithubUrl(user.profile?.github_url || "");
      setLinkedinUrl(user.profile?.linkedin_url || "");
      setPortfolioUrl(user.profile?.portfolio_url || "");
      fetchMyProjects();
    }
  }, [user]);

  const fetchMyProjects = async () => {
    try {
      const { data } = await axios.get(`${API}/projects?founder_id=me`, { withCredentials: true });
      setMyProjects(data);
    } catch (e) { console.error(e); } finally { setLoading(false); }
  };

  const saveProfile = async () => {
    setSaving(true);
    try {
      await axios.patch(`${API}/users/me`, { bio, institution, year_of_study: yearOfStudy, availability_hours: availabilityHours, risk_tolerance: riskTolerance, github_url: githubUrl, linkedin_url: linkedinUrl, portfolio_url: portfolioUrl }, { withCredentials: true });
      await refreshUser();
      setEditing(false);
      toast.success("Profile updated!");
    } catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); } finally { setSaving(false); }
  };

  const handleLogout = async () => { await logout(); navigate("/"); };

  const DomainIcon = domainIcons[user?.domain] || Code;

  return (
    <div className="min-h-screen bg-[#0D0D1A] py-12 px-6">
      <div className="max-w-4xl mx-auto">
        <Link to="/dashboard" className="flex items-center gap-2 text-[#94A3B8] hover:text-white mb-8 transition-colors"><ArrowLeft size={20} /> Back to Dashboard</Link>

        <div className="glow-card rounded-2xl p-8 mb-8">
          <div className="flex items-start justify-between mb-6">
            <div className="flex items-center gap-6">
              <div className="w-24 h-24 rounded-2xl flex items-center justify-center text-white text-3xl font-bold" style={{ background: domainColors[user?.domain] || "#6C63FF" }}>{user?.full_name?.charAt(0)}</div>
              <div>
                <h1 className="text-2xl font-bold mb-1">{user?.full_name}</h1>
                <div className="flex items-center gap-2 mb-2"><DomainIcon size={18} style={{ color: domainColors[user?.domain] }} /><span className="capitalize" style={{ color: domainColors[user?.domain] }}>{user?.domain}</span></div>
                <p className="text-sm text-[#94A3B8]">{user?.email}</p>
              </div>
            </div>
            <button onClick={() => setEditing(!editing)} className="btn-secondary flex items-center gap-2"><PencilSimple size={16} /> {editing ? "Cancel" : "Edit"}</button>
          </div>

          {editing ? (
            <div className="space-y-4">
              <div><label className="block text-sm font-medium mb-2">Bio</label><textarea value={bio} onChange={(e) => setBio(e.target.value)} placeholder="Tell us about yourself..." className="w-full px-4 py-3 rounded-xl h-24 resize-none" /></div>
              <div className="grid grid-cols-2 gap-4">
                <div><label className="flex items-center gap-2 text-sm font-medium mb-2"><GraduationCap size={16} /> Institution</label><input type="text" value={institution} onChange={(e) => setInstitution(e.target.value)} placeholder="MIT, Stanford..." className="w-full px-4 py-3 rounded-xl" /></div>
                <div><label className="block text-sm font-medium mb-2">Year of Study</label><select value={yearOfStudy} onChange={(e) => setYearOfStudy(Number(e.target.value))} className="w-full px-4 py-3 rounded-xl">{[1, 2, 3, 4, 5].map((y) => <option key={y} value={y}>Year {y}</option>)}</select></div>
              </div>
              <div><label className="flex items-center gap-2 text-sm font-medium mb-2"><Clock size={16} /> Availability: {availabilityHours}h/week</label><input type="range" min="1" max="40" value={availabilityHours} onChange={(e) => setAvailabilityHours(Number(e.target.value))} className="w-full accent-[#6C63FF]" /></div>
              <div><label className="flex items-center gap-2 text-sm font-medium mb-2"><Scales size={16} /> Risk Tolerance: {riskTolerance}/10</label><input type="range" min="1" max="10" value={riskTolerance} onChange={(e) => setRiskTolerance(Number(e.target.value))} className="w-full accent-[#6C63FF]" /></div>
              <div className="grid grid-cols-3 gap-4">
                <div><label className="flex items-center gap-2 text-sm font-medium mb-2"><GithubLogo size={16} /> GitHub</label><input type="url" value={githubUrl} onChange={(e) => setGithubUrl(e.target.value)} placeholder="https://github.com/..." className="w-full px-4 py-3 rounded-xl" /></div>
                <div><label className="flex items-center gap-2 text-sm font-medium mb-2"><LinkedinLogo size={16} /> LinkedIn</label><input type="url" value={linkedinUrl} onChange={(e) => setLinkedinUrl(e.target.value)} placeholder="https://linkedin.com/in/..." className="w-full px-4 py-3 rounded-xl" /></div>
                <div><label className="flex items-center gap-2 text-sm font-medium mb-2"><Globe size={16} /> Portfolio</label><input type="url" value={portfolioUrl} onChange={(e) => setPortfolioUrl(e.target.value)} placeholder="https://..." className="w-full px-4 py-3 rounded-xl" /></div>
              </div>
              <button onClick={saveProfile} disabled={saving} className="btn-primary w-full py-3 flex items-center justify-center gap-2">{saving ? <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div> : "Save Changes"}</button>
            </div>
          ) : (
            <div className="space-y-4">
              {bio && <p className="text-[#94A3B8]">{bio}</p>}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {institution && <div className="p-3 bg-[#141428] rounded-xl"><div className="text-xs text-[#94A3B8] mb-1">Institution</div><div className="font-medium">{institution}</div></div>}
                <div className="p-3 bg-[#141428] rounded-xl"><div className="text-xs text-[#94A3B8] mb-1">Year</div><div className="font-medium">Year {yearOfStudy}</div></div>
                <div className="p-3 bg-[#141428] rounded-xl"><div className="text-xs text-[#94A3B8] mb-1">Availability</div><div className="font-medium">{availabilityHours}h/week</div></div>
                <div className="p-3 bg-[#141428] rounded-xl"><div className="text-xs text-[#94A3B8] mb-1">Risk Tolerance</div><div className="font-medium">{riskTolerance}/10</div></div>
              </div>
              <div className="flex gap-4">
                {githubUrl && <a href={githubUrl} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-[#94A3B8] hover:text-white"><GithubLogo size={20} /> GitHub</a>}
                {linkedinUrl && <a href={linkedinUrl} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-[#94A3B8] hover:text-white"><LinkedinLogo size={20} /> LinkedIn</a>}
                {portfolioUrl && <a href={portfolioUrl} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-[#94A3B8] hover:text-white"><Globe size={20} /> Portfolio</a>}
              </div>
            </div>
          )}
        </div>

        <div className="glow-card rounded-2xl p-8 mb-8">
          <h2 className="text-xl font-bold mb-4">Skills</h2>
          {user?.skills?.length > 0 ? (
            <div className="flex flex-wrap gap-3">
              {user.skills.map((skill, i) => (
                <div key={i} className="flex items-center gap-2 px-4 py-2 rounded-full bg-[#141428] border border-white/10">
                  <span>{skill.skill_name}</span>
                  <div className="flex gap-0.5">{[1, 2, 3, 4, 5].map((p) => <Star key={p} weight={p <= skill.proficiency ? "fill" : "regular"} size={12} className={p <= skill.proficiency ? "text-[#FBBF24]" : "text-[#94A3B8]"} />)}</div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-[#94A3B8]">No skills added yet. <Link to="/onboarding" className="text-[#6C63FF] hover:underline">Add skills</Link></p>
          )}
        </div>

        <div className="glow-card rounded-2xl p-8 mb-8">
          <div className="flex items-center justify-between mb-4"><h2 className="text-xl font-bold">My Projects</h2><Link to="/projects/new" className="text-sm text-[#6C63FF] hover:underline">+ New Project</Link></div>
          {loading ? (
            <div className="animate-pulse space-y-3">{[1, 2].map((i) => <div key={i} className="h-16 bg-[#141428] rounded-xl"></div>)}</div>
          ) : myProjects.length > 0 ? (
            <div className="space-y-3">
              {myProjects.map((p) => (
                <Link key={p.id} to={`/projects/${p.id}`} className="block p-4 bg-[#141428] rounded-xl border border-white/5 hover:border-[#6C63FF]/30 transition-all">
                  <div className="flex items-center justify-between"><span className="font-medium">{p.title}</span><span className="text-xs px-2 py-1 rounded capitalize stage-{p.stage}">{p.stage}</span></div>
                </Link>
              ))}
            </div>
          ) : (
            <p className="text-[#94A3B8]">No projects yet. <Link to="/projects/new" className="text-[#6C63FF] hover:underline">Create one</Link></p>
          )}
        </div>

        <button onClick={handleLogout} className="text-red-400 hover:text-red-300 transition-colors">Sign out</button>
      </div>
    </div>
  );
}
