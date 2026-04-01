import { useState } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";
import { motion } from "framer-motion";
import axios from "axios";
import { API, formatApiErrorDetail } from "../App";
import { toast } from "sonner";
import { Rocket, ArrowLeft, ArrowRight, Sparkle, Plus, X, CheckCircle } from "@phosphor-icons/react";

const stages = [
  { id: "ideation", label: "Ideation", desc: "Early concept exploration" },
  { id: "mvp", label: "MVP", desc: "Building minimum viable product" },
  { id: "validation", label: "Validation", desc: "Testing with real users" },
  { id: "scaling", label: "Scaling", desc: "Growing and expanding" },
];

const gradeColors = { A: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30", B: "bg-blue-500/20 text-blue-400 border-blue-500/30", C: "bg-orange-500/20 text-orange-400 border-orange-500/30", D: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30", F: "bg-red-500/20 text-red-400 border-red-500/30" };

export default function ProjectNew() {
  const location = useLocation();
  const prefill = location.state?.prefill || {};
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [validationResult, setValidationResult] = useState(null);

  const [title, setTitle] = useState(prefill.title || "");
  const [description, setDescription] = useState(prefill.description || "");
  const [problemStatement, setProblemStatement] = useState(prefill.problem_statement || "");
  const [targetMarket, setTargetMarket] = useState(prefill.target_market || "");
  const [industryVertical, setIndustryVertical] = useState(prefill.industry_vertical || "");
  const [stage, setStage] = useState("ideation");
  const [maxTeamSize, setMaxTeamSize] = useState(4);

  const validateIdea = async () => {
    if (!title || !problemStatement || !targetMarket) { toast.error("Please fill in title, problem, and market"); return; }
    setValidating(true);
    try {
      const { data } = await axios.post(`${API}/ai/validate`, { title, problem: problemStatement, market: targetMarket, industry: industryVertical, description }, { withCredentials: true });
      setValidationResult(data);
    } catch (e) { toast.error("Validation failed. Try again."); } finally { setValidating(false); }
  };

  const createProject = async () => {
    if (!title || !description) { toast.error("Title and description are required"); return; }
    setLoading(true);
    try {
      const { data } = await axios.post(`${API}/projects`, { title, description, problem_statement: problemStatement, target_market: targetMarket, industry_vertical: industryVertical, stage, max_team_size: maxTeamSize }, { withCredentials: true });
      toast.success("Project created!");
      navigate(`/projects/${data.id}`);
    } catch (e) { toast.error(formatApiErrorDetail(e.response?.data?.detail)); } finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen bg-[#0D0D1A] py-12 px-6">
      <div className="max-w-3xl mx-auto">
        <Link to="/dashboard" className="flex items-center gap-2 text-[#94A3B8] hover:text-white mb-8 transition-colors">
          <ArrowLeft size={20} /> Back to Dashboard
        </Link>
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 bg-gradient-to-br from-[#6C63FF] to-[#EC4899] rounded-xl flex items-center justify-center">
            <Plus weight="bold" className="w-5 h-5 text-white" />
          </div>
          <h1 className="text-2xl font-bold">Create New Project</h1>
        </div>
        <div className="flex items-center gap-4 mb-8">
          {[1, 2, 3].map((s) => (
            <div key={s} className="flex items-center gap-2 flex-1">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold transition-all ${s < step ? "bg-[#6C63FF] text-white" : s === step ? "bg-[#6C63FF]/20 text-[#6C63FF] border-2 border-[#6C63FF]" : "bg-[#141428] text-[#94A3B8] border border-white/10"}`}>
                {s < step ? <CheckCircle weight="fill" size={20} /> : s}
              </div>
              {s < 3 && <div className={`flex-1 h-1 rounded ${s < step ? "bg-[#6C63FF]" : "bg-white/10"}`}></div>}
            </div>
          ))}
        </div>

        {step === 1 && (
          <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="glow-card rounded-2xl p-8">
            <h2 className="text-xl font-bold mb-6">Step 1: Your Idea</h2>
            <div className="space-y-4">
              <div><label className="block text-sm font-medium mb-2">Project Title *</label><input type="text" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. EcoTrack" className="w-full px-4 py-3 rounded-xl" data-testid="project-title-input" /></div>
              <div><label className="block text-sm font-medium mb-2">Description *</label><textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="What are you building?" className="w-full px-4 py-3 rounded-xl h-24 resize-none" data-testid="project-description-input" /></div>
              <div><label className="block text-sm font-medium mb-2">Problem Statement</label><textarea value={problemStatement} onChange={(e) => setProblemStatement(e.target.value)} placeholder="What problem are you solving?" className="w-full px-4 py-3 rounded-xl h-20 resize-none" data-testid="project-problem-input" /></div>
              <div className="grid grid-cols-2 gap-4">
                <div><label className="block text-sm font-medium mb-2">Target Market</label><input type="text" value={targetMarket} onChange={(e) => setTargetMarket(e.target.value)} placeholder="Who are your customers?" className="w-full px-4 py-3 rounded-xl" data-testid="project-market-input" /></div>
                <div><label className="block text-sm font-medium mb-2">Industry</label><input type="text" value={industryVertical} onChange={(e) => setIndustryVertical(e.target.value)} placeholder="e.g. CleanTech" className="w-full px-4 py-3 rounded-xl" /></div>
              </div>
            </div>

            {validationResult && (
              <div className="mt-6 p-4 bg-[#141428] rounded-xl border border-[#6C63FF]/30">
                <div className="flex items-center gap-4 mb-4">
                  <div className={`w-16 h-16 rounded-xl flex items-center justify-center text-2xl font-bold border ${gradeColors[validationResult.overall_grade] || gradeColors.C}`}>{validationResult.overall_grade}</div>
                  <div><div className="text-sm text-[#94A3B8]">Viability</div><div className="font-mono text-xl font-bold">{validationResult.viability_score}%</div></div>
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div><div className="text-emerald-400 font-medium mb-1">Green Flags</div>{validationResult.green_flags?.slice(0, 2).map((f, i) => <div key={i} className="text-[#94A3B8]">• {f}</div>)}</div>
                  <div><div className="text-amber-400 font-medium mb-1">Red Flags</div>{validationResult.red_flags?.slice(0, 2).map((f, i) => <div key={i} className="text-[#94A3B8]">• {f}</div>)}</div>
                </div>
              </div>
            )}

            <div className="flex gap-4 mt-8">
              <button onClick={validateIdea} disabled={validating} className="btn-secondary flex-1 py-4 flex items-center justify-center gap-2" data-testid="validate-idea-btn">
                {validating ? <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-[#6C63FF]"></div> : <><Sparkle weight="fill" /> Validate Idea</>}
              </button>
              <button onClick={() => setStep(2)} className="btn-primary flex-1 py-4 flex items-center justify-center gap-2" data-testid="step1-next-btn">
                Next <ArrowRight weight="bold" />
              </button>
            </div>
          </motion.div>
        )}

        {step === 2 && (
          <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="glow-card rounded-2xl p-8">
            <h2 className="text-xl font-bold mb-6">Step 2: Stage & Team</h2>
            <div className="space-y-6">
              <div><label className="block text-sm font-medium mb-3">Project Stage</label>
                <div className="grid grid-cols-2 gap-3">
                  {stages.map((s) => (
                    <button key={s.id} onClick={() => setStage(s.id)} className={`p-4 rounded-xl border-2 text-left transition-all ${stage === s.id ? "border-[#6C63FF] bg-[#6C63FF]/10" : "border-white/10 hover:border-white/30"}`} data-testid={`stage-${s.id}-btn`}>
                      <div className="font-medium">{s.label}</div>
                      <div className="text-xs text-[#94A3B8]">{s.desc}</div>
                    </button>
                  ))}
                </div>
              </div>
              <div><label className="block text-sm font-medium mb-2">Max Team Size: {maxTeamSize}</label><input type="range" min="2" max="8" value={maxTeamSize} onChange={(e) => setMaxTeamSize(Number(e.target.value))} className="w-full accent-[#6C63FF]" /><div className="flex justify-between text-xs text-[#94A3B8]"><span>2</span><span>8</span></div></div>
            </div>
            <div className="flex gap-4 mt-8">
              <button onClick={() => setStep(1)} className="btn-secondary flex-1 py-4"><ArrowLeft weight="bold" className="inline mr-2" /> Back</button>
              <button onClick={() => setStep(3)} className="btn-primary flex-1 py-4 flex items-center justify-center gap-2" data-testid="step2-next-btn">Next <ArrowRight weight="bold" /></button>
            </div>
          </motion.div>
        )}

        {step === 3 && (
          <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="glow-card rounded-2xl p-8">
            <h2 className="text-xl font-bold mb-6">Step 3: Review & Create</h2>
            <div className="space-y-4 mb-8">
              <div className="flex justify-between py-3 border-b border-white/10"><span className="text-[#94A3B8]">Title</span><span className="font-medium">{title}</span></div>
              <div className="flex justify-between py-3 border-b border-white/10"><span className="text-[#94A3B8]">Stage</span><span className="font-medium capitalize">{stage}</span></div>
              <div className="flex justify-between py-3 border-b border-white/10"><span className="text-[#94A3B8]">Team Size</span><span className="font-medium">Up to {maxTeamSize}</span></div>
              {industryVertical && <div className="flex justify-between py-3 border-b border-white/10"><span className="text-[#94A3B8]">Industry</span><span className="font-medium">{industryVertical}</span></div>}
              <div className="py-3"><span className="text-[#94A3B8] block mb-2">Description</span><p className="text-sm">{description}</p></div>
            </div>
            <div className="flex gap-4">
              <button onClick={() => setStep(2)} className="btn-secondary flex-1 py-4"><ArrowLeft weight="bold" className="inline mr-2" /> Back</button>
              <button onClick={createProject} disabled={loading} className="btn-primary flex-1 py-4 flex items-center justify-center gap-2" data-testid="create-project-submit-btn">
                {loading ? <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div> : <><Rocket weight="fill" /> Create Project</>}
              </button>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
