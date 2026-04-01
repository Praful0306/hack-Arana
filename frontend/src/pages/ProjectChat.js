import { useState, useEffect, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import axios from "axios";
import { API, useAuth } from "../App";
import { toast } from "sonner";
import { ArrowLeft, PaperPlaneTilt, Robot, User, Lightning, Lightbulb, Users } from "@phosphor-icons/react";
import ReactMarkdown from "react-markdown";

const suggestedPrompts = [
  { icon: Lightning, text: "What should we build in Sprint 1?" },
  { icon: Users, text: "Who should we recruit next?" },
  { icon: Lightbulb, text: "What's our biggest risk right now?" },
];

const domainColors = { engineering: "#3B82F6", design: "#EC4899", business: "#10B981" };

export default function ProjectChat() {
  const { id } = useParams();
  const { user } = useAuth();
  const [project, setProject] = useState(null);
  const [team, setTeam] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => { fetchProject(); }, [id]);
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const fetchProject = async () => {
    setLoading(true);
    try {
      const [projRes, teamRes] = await Promise.all([
        axios.get(`${API}/projects/${id}`, { withCredentials: true }),
        axios.get(`${API}/teams/${id}`, { withCredentials: true }).catch(() => ({ data: null })),
      ]);
      setProject(projRes.data);
      setTeam(teamRes.data);
      setMessages([{ role: "assistant", content: `Hi ${user?.full_name?.split(" ")[0] || "there"}! I'm your AI co-founder for **${projRes.data.title}**. I know your team, your milestones, and your current stage. Ask me anything about building your startup!` }]);
    } catch (e) { toast.error("Failed to load project"); } finally { setLoading(false); }
  };

  const sendMessage = async (text) => {
    if (!text.trim()) return;
    const userMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setSending(true);
    try {
      const history = messages.map((m) => ({ role: m.role, content: m.content }));
      const { data } = await axios.post(`${API}/ai/chat/${id}`, { message: text, conversation_history: history }, { withCredentials: true });
      setMessages((prev) => [...prev, { role: "assistant", content: data.reply }]);
    } catch (e) {
      toast.error("Failed to get response");
      setMessages((prev) => [...prev, { role: "assistant", content: "Sorry, I encountered an error. Please try again." }]);
    } finally { setSending(false); }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(input); }
  };

  if (loading) return <div className="min-h-screen bg-[#0D0D1A] flex items-center justify-center"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#6C63FF]"></div></div>;

  return (
    <div className="min-h-screen bg-[#0D0D1A] flex flex-col">
      <header className="glass px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link to={`/projects/${id}`} className="text-[#94A3B8] hover:text-white"><ArrowLeft size={24} /></Link>
          <div>
            <div className="flex items-center gap-2"><h1 className="font-semibold">{project?.title}</h1><span className="ai-badge">✦ AI Chat</span></div>
            <p className="text-xs text-[#94A3B8]">{project?.stage} stage</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {team?.members?.slice(0, 4).map((m, i) => (
            <div key={i} className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-semibold -ml-2 first:ml-0 border-2 border-[#0D0D1A]" style={{ background: domainColors[m.domain] }}>{m.name?.charAt(0)}</div>
          ))}
        </div>
      </header>

      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.map((msg, i) => (
          <motion.div key={i} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`flex items-start gap-3 max-w-2xl ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
              <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${msg.role === "user" ? "" : "bg-[#6C63FF]"}`} style={msg.role === "user" ? { background: domainColors[user?.domain] || "#6C63FF" } : {}}>
                {msg.role === "user" ? <span className="text-white font-semibold">{user?.full_name?.charAt(0)}</span> : <Robot weight="fill" className="text-white" size={20} />}
              </div>
              <div className={`p-4 rounded-2xl ${msg.role === "user" ? "bg-[#6C63FF] text-white" : "bg-[#141428] border border-white/10"}`}>
                {msg.role === "assistant" ? (
                  <div className="prose prose-invert prose-sm max-w-none">
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                ) : (
                  <p>{msg.content}</p>
                )}
              </div>
            </div>
          </motion.div>
        ))}
        {sending && (
          <div className="flex justify-start">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-full bg-[#6C63FF] flex items-center justify-center"><Robot weight="fill" className="text-white" size={20} /></div>
              <div className="bg-[#141428] border border-white/10 rounded-2xl p-4"><div className="typing-indicator"><span></span><span></span><span></span></div></div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {messages.length === 1 && (
        <div className="px-6 pb-4">
          <div className="flex flex-wrap gap-2 justify-center">
            {suggestedPrompts.map((prompt, i) => (
              <button key={i} onClick={() => sendMessage(prompt.text)} className="flex items-center gap-2 px-4 py-2 rounded-full bg-[#141428] border border-white/10 hover:border-[#6C63FF] transition-all text-sm" data-testid={`suggested-prompt-${i}`}>
                <prompt.icon size={16} className="text-[#6C63FF]" /> {prompt.text}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="p-6 border-t border-white/10">
        <div className="max-w-3xl mx-auto flex items-end gap-4">
          <textarea value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={handleKeyDown} placeholder="Ask your AI co-founder anything..." className="flex-1 px-4 py-3 rounded-xl resize-none h-12 max-h-32" rows={1} data-testid="chat-input" />
          <button onClick={() => sendMessage(input)} disabled={sending || !input.trim()} className="btn-primary p-3 rounded-xl disabled:opacity-50" data-testid="send-message-btn">
            <PaperPlaneTilt weight="fill" size={20} />
          </button>
        </div>
      </div>
    </div>
  );
}
