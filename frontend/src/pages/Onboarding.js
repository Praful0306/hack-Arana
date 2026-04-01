import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import axios from "axios";
import { API, useAuth, formatApiErrorDetail } from "../App";
import { toast } from "sonner";
import { Rocket, User, Lightning, CheckCircle, ArrowRight, ArrowLeft, Star, GraduationCap, Clock, Scales, Sparkle } from "@phosphor-icons/react";

export default function Onboarding() {
  const [step, setStep] = useState(1);
  const { user, refreshUser } = useAuth();
  const navigate = useNavigate();
  const [bio, setBio] = useState("");
  const [institution, setInstitution] = useState("");
  const [yearOfStudy, setYearOfStudy] = useState(2);
  const [availabilityHours, setAvailabilityHours] = useState(10);
  const [riskTolerance, setRiskTolerance] = useState(5);
  const [skillsTaxonomy, setSkillsTaxonomy] = useState({});
  const [selectedSkills, setSelectedSkills] = useState([]);
  const [loading, setLoading] = useState(false);
  const [ideaTitle, setIdeaTitle] = useState("");
  const [ideaProblem, setIdeaProblem] = useState("");
  const [ideaMarket, setIdeaMarket] = useState("");
  const [ideaIndustry, setIdeaIndustry] = useState("");
  const [ideaDescription, setIdeaDescription] = useState("");
  const [validationResult, setValidationResult] = useState(null);
  const [validating, setValidating] = useState(false);

  useEffect(() => { fetchSkillsTaxonomy(); }, []);

  const fetchSkillsTaxonomy = async () => {
    try {
      const { data } = await axios.get(`${API}/users/skills/taxonomy`, { withCredentials: true });
      setSkillsTaxonomy(data);
    } catch (e) { console.error("Failed to fetch skills", e); }
  };

  const toggleSkill = (skillId, skillName, domain) => {
    const existing = selectedSkills.find((s) => s.skill_id === skillId);
    if (existing) { setSelectedSkills(selectedSkills.filter((s) => s.skill_id !== skillId)); }
    else { setSelectedSkills([...selectedSkills, { skill_id: skillId, skill_name: skillName, domain, proficiency: 3 }]); }
  };

  const updateProficiency = (skillId, proficiency) => {
    setSelectedSkills(selectedSkills.map((s) => (s.skill_id === skillId ? { ...s, proficiency } : s)));
  };

  const handleStep1 = async () => {
    setLoading(true);
    try {
      await axios.patch(`${API}/users/me`, { bio, institution, year_of_study: yearOfStudy, availability_hours: availabilityHours, risk_tolerance: riskTolerance }, { withCredentials: true });
      setStep(2);
    } catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); } finally { setLoading(false); }
  };

  const handleStep2 = async () => {
    if (selectedSkills.length === 0) { toast.error("Please select at least one skill"); return; }
    setLoading(true);
    try {
      await axios.post(`${API}/users/me/skills`, selectedSkills.map((s) => ({ skill_id: s.skill_id, proficiency: s.proficiency })), { withCredentials: true });
      setStep(3);
    } catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); } finally { setLoading(false); }
  };

  const validateIdea = async () => {
    if (!ideaTitle || !ideaProblem || !ideaMarket) { toast.error("Please fill in title, problem, and market"); return; }
    setValidating(true);
    try {
      const { data } = await axios.post(`${API}/ai/validate`, { title: ideaTitle, problem: ideaProblem, market: ideaMarket, industry: ideaIndustry, description: ideaDescription }, { withCredentials: true });
      setValidationResult(data);
    } catch (e) { toast.error("Validation failed. Try again."); } finally { setValidating(false); }
  };

  const finishOnboarding = async () => {
    setLoading(true);
    try {
      await axios.post(`${API}/users/me/complete-onboarding`, {}, { withCredentials: true });
      await refreshUser();
      toast.success("Welcome to Antigravity!");
      navigate("/dashboard");
    } catch (e) { toast.error("Failed to complete onboarding"); } finally { setLoading(false); }
  };

  const createProjectFromIdea = async () => {
    setLoading(true);
    try {
      await axios.post(`${API}/users/me/complete-onboarding`, {}, { withCredentials: true });
      await refreshUser();
      navigate("/projects/new", { state: { prefill: { title: ideaTitle, problem_statement: ideaProblem, target_market: ideaMarket, industry_vertical: ideaIndustry, description: ideaDescription } } });
    } catch (e) { toast.error("Failed to continue"); } finally { setLoading(false); }
  };

  const gradeColors = { A: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30", B: "bg-blue-500/20 text-blue-400 border-blue-500/30", C: "bg-orange-500/20 text-orange-400 border-orange-500/30", D: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30", F: "bg-red-500/20 text-red-400 border-red-500/30" };

  return (
    <div className="min-h-screen bg-[#0D0D1A] py-12 px-6">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 bg-gradient-to-br from-[#6C63FF] to-[#EC4899] rounded-xl flex items-center justify-center">
            <Rocket weight="fill" className="w-5 h-5 text-white" />
          </div>
          <span className="font-bold text-xl">Antigravity</span>
        </div>
        <div className="flex items-center gap-4 mb-12">
          {[1, 2, 3].map((s) => (
            <div key={s} className="flex items-center gap-2 flex-1">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold transition-all ${s < step ? "bg-[#6C63FF] text-white" : s === step ? "bg-[#6C63FF]/20 text-[#6C63FF] border-2 border-[#6C63FF]" : "bg-[#141428] text-[#94A3B8] border border-white/10"}`}>
                {s < step ? <CheckCircle weight="fill" size={20} /> : s}
              </div>
              {s < 3 && <div className={`flex-1 h-1 rounded ${s < step ? "bg-[#6C63FF]" : "bg-white/10"}`}></div>}
            </div>
          ))}
        </div>
        <AnimatePresence mode="wait">
          {step === 1 && (
            <motion.div key="step1" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="glow-card rounded-2xl p-8">
              <div className="flex items-center gap-3 mb-6"><User weight="duotone" size={28} className="text-[#6C63FF]" /><h2 className="text-2xl font-bold">Tell us about yourself</h2></div>
              <div className="space-y-6">
                <div><label className="block text-sm font-medium mb-2">Bio</label><textarea value={bio} onChange={(e) => setBio(e.target.value)} placeholder="A short intro..." className="w-full px-4 py-3 rounded-xl h-24 resize-none" data-testid="onboarding-bio-input" /></div>
                <div className="grid grid-cols-2 gap-6">
                  <div><label className="flex items-center gap-2 text-sm font-medium mb-2"><GraduationCap size={16} /> Institution</label><input type="text" value={institution} onChange={(e) => setInstitution(e.target.value)} placeholder="MIT, Stanford..." className="w-full px-4 py-3 rounded-xl" data-testid="onboarding-institution-input" /></div>
                  <div><label className="block text-sm font-medium mb-2">Year of Study</label><select value={yearOfStudy} onChange={(e) => setYearOfStudy(Number(e.target.value))} className="w-full px-4 py-3 rounded-xl" data-testid="onboarding-year-select">{[1, 2, 3, 4, 5].map((y) => <option key={y} value={y}>Year {y}</option>)}</select></div>
                </div>
                <div><label className="flex items-center gap-2 text-sm font-medium mb-2"><Clock size={16} /> Availability: {availabilityHours}h/week</label><input type="range" min="1" max="40" value={availabilityHours} onChange={(e) => setAvailabilityHours(Number(e.target.value))} className="w-full accent-[#6C63FF]" data-testid="onboarding-availability-slider" /><div className="flex justify-between text-xs text-[#94A3B8]"><span>1h</span><span>40h</span></div></div>
                <div><label className="flex items-center gap-2 text-sm font-medium mb-2"><Scales size={16} /> Risk Tolerance: {riskTolerance}/10</label><input type="range" min="1" max="10" value={riskTolerance} onChange={(e) => setRiskTolerance(Number(e.target.value))} className="w-full accent-[#6C63FF]" data-testid="onboarding-risk-slider" /><div className="flex justify-between text-xs text-[#94A3B8]"><span>Conservative</span><span>Bold</span></div></div>
              </div>
              <button onClick={handleStep1} disabled={loading} className="btn-primary w-full mt-8 py-4 flex items-center justify-center gap-2" data-testid="onboarding-step1-next-btn">{loading ? <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div> : <>Next <ArrowRight weight="bold" /></>}</button>
            </motion.div>
          )}
          {step === 2 && (
            <motion.div key="step2" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="glow-card rounded-2xl p-8">
              <div className="flex items-center gap-3 mb-6"><Lightning weight="duotone" size={28} className="text-[#6C63FF]" /><h2 className="text-2xl font-bold">Add your skills</h2></div>
              <p className="text-[#94A3B8] mb-6">Select skills and rate proficiency (1-5 stars)</p>
              {Object.entries(skillsTaxonomy).map(([domain, skills]) => (
                <div key={domain} className="mb-6">
                  <h3 className={`text-sm font-semibold uppercase tracking-wider mb-3 ${domain === "engineering" ? "text-[#3B82F6]" : domain === "design" ? "text-[#EC4899]" : "text-[#10B981]"}`}>{domain}</h3>
                  <div className="flex flex-wrap gap-2">
                    {skills.map((skill) => {
                      const selected = selectedSkills.find((s) => s.skill_id === skill.id);
                      return (
                        <div key={skill.id} className="relative">
                          <button onClick={() => toggleSkill(skill.id, skill.name, domain)} className={`px-4 py-2 rounded-full text-sm transition-all ${selected ? "bg-[#6C63FF] text-white" : "bg-[#141428] border border-white/10 hover:border-[#6C63FF]"}`} data-testid={`skill-${skill.id}-btn`}>{skill.name}</button>
                          {selected && <div className="flex items-center gap-0.5 mt-2 justify-center">{[1, 2, 3, 4, 5].map((p) => <button key={p} onClick={() => updateProficiency(skill.id, p)} className="p-0.5"><Star weight={p <= selected.proficiency ? "fill" : "regular"} size={14} className={p <= selected.proficiency ? "text-[#FBBF24]" : "text-[#94A3B8]"} /></button>)}</div>}
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
              <div className="flex gap-4 mt-8"><button onClick={() => setStep(1)} className="btn-secondary flex-1 py-4 flex items-center justify-center gap-2"><ArrowLeft weight="bold" /> Back</button><button onClick={handleStep2} disabled={loading} className="btn-primary flex-1 py-4 flex items-center justify-center gap-2" data-testid="onboarding-step2-next-btn">{loading ? <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div> : <>Next <ArrowRight weight="bold" /></>}</button></div>
            </motion.div>
          )}
          {step === 3 && (
            <motion.div key="step3" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="glow-card rounded-2xl p-8">
              <div className="flex items-center gap-3 mb-2"><Sparkle weight="duotone" size={28} className="text-[#6C63FF]" /><h2 className="text-2xl font-bold">Validate Your Idea</h2><span className="ai-badge ml-2">✦ AI</span></div>
              <p className="text-[#94A3B8] mb-6">Optional: Get instant AI feedback on your startup idea</p>
              {!validationResult ? (
                <div className="space-y-4">
                  <div><label className="block text-sm font-medium mb-2">Idea Title</label><input type="text" value={ideaTitle} onChange={(e) => setIdeaTitle(e.target.value)} placeholder="e.g. EcoTrack - Carbon Tracker" className="w-full px-4 py-3 rounded-xl" data-testid="idea-title-input" /></div>
                  <div><label className="block text-sm font-medium mb-2">Problem</label><textarea value={ideaProblem} onChange={(e) => setIdeaProblem(e.target.value)} placeholder="What problem does it solve?" className="w-full px-4 py-3 rounded-xl h-20 resize-none" data-testid="idea-problem-input" /></div>
                  <div><label className="block text-sm font-medium mb-2">Target Market</label><input type="text" value={ideaMarket} onChange={(e) => setIdeaMarket(e.target.value)} placeholder="Who are your customers?" className="w-full px-4 py-3 rounded-xl" data-testid="idea-market-input" /></div>
                  <div className="grid grid-cols-2 gap-4"><div><label className="block text-sm font-medium mb-2">Industry</label><input type="text" value={ideaIndustry} onChange={(e) => setIdeaIndustry(e.target.value)} placeholder="e.g. CleanTech" className="w-full px-4 py-3 rounded-xl" /></div><div><label className="block text-sm font-medium mb-2">Description</label><input type="text" value={ideaDescription} onChange={(e) => setIdeaDescription(e.target.value)} placeholder="Brief solution" className="w-full px-4 py-3 rounded-xl" /></div></div>
                  <div className="flex gap-4 mt-6"><button onClick={() => setStep(2)} className="btn-secondary flex-1 py-4"><ArrowLeft weight="bold" className="inline mr-2" /> Back</button><button onClick={validateIdea} disabled={validating} className="btn-primary flex-1 py-4 flex items-center justify-center gap-2" data-testid="validate-idea-btn">{validating ? <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div> : <><Sparkle weight="fill" /> Validate</>}</button></div>
                  <button onClick={finishOnboarding} className="w-full text-[#94A3B8] hover:text-white py-3 transition-colors" data-testid="skip-validation-btn">Skip this step</button>
                </div>
              ) : (
                <div className="space-y-6">
                  <div className="flex items-center gap-6"><div className={`w-24 h-24 rounded-2xl flex items-center justify-center text-4xl font-bold border ${gradeColors[validationResult.overall_grade] || gradeColors.C}`}>{validationResult.overall_grade}</div><div><div className="text-sm text-[#94A3B8] mb-1">Viability Score</div><div className="flex items-center gap-3"><div className="w-32 h-3 bg-[#141428] rounded-full overflow-hidden"><div className="h-full bg-gradient-to-r from-[#6C63FF] to-[#EC4899] rounded-full" style={{ width: `${validationResult.viability_score}%` }}></div></div><span className="font-mono font-bold">{validationResult.viability_score}%</span></div></div></div>
                  <div><div className="text-sm font-medium mb-3">Recommended Team</div><div className="flex items-center gap-2"><div className="flex-1 h-4 rounded-full overflow-hidden flex"><div className="bg-[#3B82F6]" style={{ width: `${validationResult.recommended_team_composition?.engineering_pct || 33}%` }}></div><div className="bg-[#EC4899]" style={{ width: `${validationResult.recommended_team_composition?.design_pct || 33}%` }}></div><div className="bg-[#10B981]" style={{ width: `${validationResult.recommended_team_composition?.business_pct || 34}%` }}></div></div></div><div className="flex justify-between text-xs mt-1 text-[#94A3B8]"><span>Eng {validationResult.recommended_team_composition?.engineering_pct}%</span><span>Design {validationResult.recommended_team_composition?.design_pct}%</span><span>Biz {validationResult.recommended_team_composition?.business_pct}%</span></div></div>
                  <div className="grid grid-cols-2 gap-4"><div><div className="text-sm font-medium mb-2 text-emerald-400">Green Flags</div><ul className="space-y-1">{validationResult.green_flags?.map((f, i) => <li key={i} className="text-sm text-[#94A3B8]">• {f}</li>)}</ul></div><div><div className="text-sm font-medium mb-2 text-amber-400">Red Flags</div><ul className="space-y-1">{validationResult.red_flags?.map((f, i) => <li key={i} className="text-sm text-[#94A3B8]">• {f}</li>)}</ul></div></div>
                  <div className="bg-[#141428] rounded-xl p-4 border-l-4 border-[#6C63FF]"><div className="text-sm font-medium mb-1">MVP Suggestion</div><p className="text-[#94A3B8] text-sm italic">"{validationResult.mvp_suggestion}"</p></div>
                  <p className="text-sm text-[#94A3B8]">{validationResult.verdict}</p>
                  <div className="flex gap-4"><button onClick={() => setValidationResult(null)} className="btn-secondary flex-1 py-4">Try Another</button><button onClick={createProjectFromIdea} disabled={loading} className="btn-primary flex-1 py-4 flex items-center justify-center gap-2" data-testid="create-project-from-idea-btn">{loading ? <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div> : <>Create Project <ArrowRight weight="bold" /></>}</button></div>
                  <button onClick={finishOnboarding} className="w-full text-[#94A3B8] hover:text-white py-3 transition-colors">Go to Dashboard</button>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
